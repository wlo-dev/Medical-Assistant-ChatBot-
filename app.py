"""
Flask backend for the Medical Assistant Chatbot UI.

Wraps the RAG pipeline (Pinecone + HuggingFace embeddings + Ollama) behind
a small JSON/streaming API. Conversations are persisted as JSON files on
disk under conversations/, so previous chats survive app restarts and can
be revisited from the sidebar.
"""

import json
import os
import time
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, render_template, Response
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

app = Flask(__name__)

CONVERSATIONS_DIR = Path(__file__).parent / "conversations"
CONVERSATIONS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Build the RAG chain once at startup
# ---------------------------------------------------------------------------

def build_rag_chain():
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_pinecone import PineconeVectorStore
    from langchain_ollama import ChatOllama
    from langchain_classic.chains import create_retrieval_chain, create_history_aware_retriever
    from langchain_classic.chains.combine_documents import create_stuff_documents_chain
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    docsearch = PineconeVectorStore.from_existing_index(
        index_name="medicalbot",
        embedding=embeddings,
    )
    retriever = docsearch.as_retriever(search_kwargs={"k": 3})

    llm = ChatOllama(model="llama3.2", temperature=0.4, keep_alive="30m")

    contextualize_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Given the chat history and the latest user question, rewrite the "
         "question as a standalone question that includes any necessary "
         "context from the conversation (for example, the condition or "
         "topic being discussed). Do not answer it — only rewrite it. "
         "If it is already standalone, return it unchanged."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_prompt
    )

    system_prompt = (
        "You are a medical information assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If the context doesn't contain enough information "
        "to answer, say that you don't know. Do not use outside knowledge "
        "or make assumptions beyond what's given. Keep the answer clear "
        "and well organized, using a few short paragraphs or a bullet "
        "list where that helps readability.\n\n"
        "This is general medical information only, not a diagnosis or "
        "treatment plan. For specific health concerns, remind the user "
        "to consult a licensed healthcare provider. If the question "
        "describes a medical emergency, tell the user to seek emergency "
        "care immediately instead of answering from context."
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(history_aware_retriever, question_answer_chain)


print("Loading RAG chain... (this can take a few seconds while Ollama warms up)")
rag_chain = build_rag_chain()
print("RAG chain ready.")


# ---------------------------------------------------------------------------
# 2. Conversation persistence helpers
# ---------------------------------------------------------------------------

def conversation_path(conversation_id):
    safe_id = "".join(c for c in conversation_id if c.isalnum() or c == "-")
    return CONVERSATIONS_DIR / f"{safe_id}.json"


def load_conversation(conversation_id):
    path = conversation_path(conversation_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_conversation(conversation):
    path = conversation_path(conversation["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)


def list_conversations():
    items = []
    for path in CONVERSATIONS_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items.append({
                "id": data["id"],
                "title": data.get("title", "New conversation"),
                "updated_at": data.get("updated_at", 0),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    items.sort(key=lambda c: c["updated_at"], reverse=True)
    return items


def messages_to_chat_history(messages):
    """Convert stored {role, text} messages into LangChain message objects."""
    history = []
    for m in messages:
        if m["role"] == "user":
            history.append(HumanMessage(content=m["text"]))
        else:
            history.append(AIMessage(content=m["text"]))
    return history


def make_title(first_message):
    title = first_message.strip().replace("\n", " ")
    return title[:48] + ("…" if len(title) > 48 else "")


# ---------------------------------------------------------------------------
# 3. Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/conversations", methods=["GET"])
def get_conversations():
    return jsonify(list_conversations())


@app.route("/api/conversations/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    convo = load_conversation(conversation_id)
    if not convo:
        return jsonify({"error": "Not found"}), 404
    return jsonify(convo)


@app.route("/api/new", methods=["POST"])
def new_conversation():
    conversation_id = str(uuid.uuid4())
    convo = {
        "id": conversation_id,
        "title": "New conversation",
        "updated_at": time.time(),
        "messages": [],
    }
    save_conversation(convo)
    return jsonify(convo)


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    data = request.get_json(force=True)
    message = (data or {}).get("message", "").strip()
    conversation_id = (data or {}).get("conversation_id", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400
    if not conversation_id:
        return jsonify({"error": "Missing conversation_id."}), 400

    convo = load_conversation(conversation_id)
    if convo is None:
        convo = {
            "id": conversation_id,
            "title": "New conversation",
            "updated_at": time.time(),
            "messages": [],
        }

    chat_history = messages_to_chat_history(convo["messages"])

    def generate():
        sources = []
        full_answer = ""
        try:
            for chunk in rag_chain.stream({
                "input": message,
                "chat_history": chat_history,
            }):
                if "context" in chunk:
                    for doc in chunk["context"][:3]:
                        src = getattr(doc, "metadata", {}).get("source")
                        if src and src not in sources:
                            sources.append(src)

                if "answer" in chunk and chunk["answer"]:
                    full_answer += chunk["answer"]
                    piece = {"type": "token", "text": chunk["answer"]}
                    yield f"data: {json.dumps(piece)}\n\n"

            is_first_message = len(convo["messages"]) == 0
            convo["messages"].append({"role": "user", "text": message, "sources": []})
            convo["messages"].append({"role": "bot", "text": full_answer, "sources": sources})
            convo["updated_at"] = time.time()
            if is_first_message:
                convo["title"] = make_title(message)
            save_conversation(convo)

            done = {
                "type": "done",
                "sources": sources,
                "conversation_id": convo["id"],
                "title": convo["title"],
            }
            yield f"data: {json.dumps(done)}\n\n"

        except Exception as exc:
            app.logger.exception("Streaming chat error")
            err = {"type": "error", "text": f"Something went wrong: {exc}"}
            yield f"data: {json.dumps(err)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)