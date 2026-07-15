"""
Flask backend for the Medical Assistant Chatbot UI.

This wraps your existing RAG pipeline (Pinecone + HuggingFace embeddings +
Ollama) behind a small JSON API that the frontend calls.

Drop this file into your project root (next to your .env), then fill in
the `build_rag_chain()` function below with the exact same setup you
already have working in your notebook: embeddings, docsearch, llm,
prompt, question_answer_chain, rag_chain.
"""

import json
import os
from flask import Flask, request, jsonify, render_template, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------------------------
# 1. Build the RAG chain once at startup (reuses your existing notebook code)
# ---------------------------------------------------------------------------

def build_rag_chain():
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_pinecone import PineconeVectorStore
    from langchain_ollama import ChatOllama
    from langchain_classic.chains import create_retrieval_chain
    from langchain_classic.chains.combine_documents import create_stuff_documents_chain
    from langchain_core.prompts import ChatPromptTemplate

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    docsearch = PineconeVectorStore.from_existing_index(
        index_name="medicalbot",
        embedding=embeddings,
    )
    retriever = docsearch.as_retriever(search_kwargs={"k": 3})

    llm = ChatOllama(model="llama3.2", temperature=0.4)

    system_prompt = (
        "You are a medical information assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If the context doesn't contain enough information "
        "to answer, say that you don't know. Do not use outside knowledge "
        "or make assumptions beyond what's given. Use three sentences "
        "maximum and keep the answer concise.\n\n"
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
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, question_answer_chain)


print("Loading RAG chain... (this can take a few seconds while Ollama warms up)")
rag_chain = build_rag_chain()
print("RAG chain ready.")


# ---------------------------------------------------------------------------
# 2. Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    message = (data or {}).get("message", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    try:
        response = rag_chain.invoke({"input": message})
        answer = response.get("answer", "").strip() or "I don't know based on the available information."

        sources = []
        for doc in response.get("context", [])[:3]:
            src = doc.metadata.get("source") if hasattr(doc, "metadata") else None
            if src and src not in sources:
                sources.append(src)

        return jsonify({"answer": answer, "sources": sources})

    except Exception as exc:
        app.logger.exception("Chat pipeline error")
        return jsonify({"error": f"Something went wrong: {exc}"}), 500


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    data = request.get_json(force=True)
    message = (data or {}).get("message", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    def generate():
        sources = []
        try:
            for chunk in rag_chain.stream({"input": message}):
                # First chunk(s) typically contain "context" (retrieved docs)
                if "context" in chunk:
                    for doc in chunk["context"][:3]:
                        src = getattr(doc, "metadata", {}).get("source")
                        if src and src not in sources:
                            sources.append(src)

                # Subsequent chunks contain incremental "answer" text
                if "answer" in chunk and chunk["answer"]:
                    piece = {"type": "token", "text": chunk["answer"]}
                    yield f"data: {json.dumps(piece)}\n\n"

            done = {"type": "done", "sources": sources}
            yield f"data: {json.dumps(done)}\n\n"

        except Exception as exc:
            app.logger.exception("Streaming chat error")
            err = {"type": "error", "text": f"Something went wrong: {exc}"}
            yield f"data: {json.dumps(err)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)