"""
Flask backend for the Medical Assistant Chatbot UI.

This wraps your existing RAG pipeline (Pinecone + HuggingFace embeddings +
Ollama) behind a small JSON API that the frontend calls. It keeps a single
running conversation history in memory so follow-up questions ("what is
the cause?") are understood in context of the previous question.
"""

import json
import os
from flask import Flask, request, jsonify, render_template, Response
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------------------------
# 1. Build the RAG chain once at startup (reuses your existing notebook code)
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

    # --- Step 1: rewrite follow-up questions into standalone questions ---
    # e.g. "what is the cause?" -> "what is the cause of AIDS?"
    # using the chat history so far.
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

    # --- Step 2: answer using the retrieved context ---
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

# In-memory conversation history for this single local session.
# Cleared whenever the user clicks "New conversation".
chat_history = []


# ---------------------------------------------------------------------------
# 2. Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/new", methods=["POST"])
def new_conversation():
    chat_history.clear()
    return jsonify({"ok": True})


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    data = request.get_json(force=True)
    message = (data or {}).get("message", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

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

            # Save this turn to history so follow-up questions have context
            chat_history.append(HumanMessage(content=message))
            chat_history.append(AIMessage(content=full_answer))

            done = {"type": "done", "sources": sources}
            yield f"data: {json.dumps(done)}\n\n"

        except Exception as exc:
            app.logger.exception("Streaming chat error")
            err = {"type": "error", "text": f"Something went wrong: {exc}"}
            yield f"data: {json.dumps(err)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)