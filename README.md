<p align="center">
  <img src="assets/banner.png" alt="MedicAsk Banner" width="100%">
</p>

<h1 align="center"> MedicAsk</h1>

<p align="center">
  <strong>An AI-powered Retrieval-Augmented Generation (RAG) medical assistant built with LangChain, Pinecone, Ollama, and Flask.</strong>
</p>

<p align="center">
  Grounded answers • Local inference • Source citations • Context-aware conversations
</p>

<p align="center">
 <p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/Flask-Backend-black?style=for-the-badge&logo=flask">
  <img src="https://img.shields.io/badge/HTML5-Markup-E34F26?style=for-the-badge&logo=html5&logoColor=white">
  <img src="https://img.shields.io/badge/CSS3-Styling-1572B6?style=for-the-badge&logo=css3&logoColor=white">
  <img src="https://img.shields.io/badge/JavaScript-Frontend-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black">
  <img src="https://img.shields.io/badge/LangChain-RAG-green?style=for-the-badge">
  <img src="https://img.shields.io/badge/Ollama-Llama_3.2-grey?style=for-the-badge">
  <img src="https://img.shields.io/badge/Pinecone-Vector_DB-00C7B7?style=for-the-badge">
</p>
</p>


## 📖 Overview

MedicAsk is a Retrieval-Augmented Generation (RAG) chatbot that answers medical questions using information retrieved from an indexed medical reference document instead of relying solely on an LLM's general knowledge.

When a user asks a question, MedicAsk searches a curated medical knowledge base for the most relevant information before generating a response. Every answer is grounded in the retrieved context and includes a source citation, making responses more transparent and reliable.

The application features a responsive web interface built with Flask, HTML, CSS, and JavaScript. Users can upload documents, ask questions, and receive streamed responses with source citations in real time. Follow-up questions are understood through conversation-aware retrieval, allowing interactions to feel more natural while keeping responses grounded in the indexed reference material.

To keep the project private and cost-effective, language generation runs locally using **Llama 3.2 through Ollama**, while document embeddings are generated locally using **all-MiniLM-L6-v2**. Pinecone is used only for storing vector embeddings of the indexed reference document.

This project was built to explore modern Retrieval-Augmented Generation architectures, semantic search, vector databases, and local large language model deployment while gaining practical experience with AI engineering concepts.
