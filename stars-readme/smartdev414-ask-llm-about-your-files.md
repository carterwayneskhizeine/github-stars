# 🚀 Semantic Search Platform

A powerful full-stack platform combining intelligent vector search capabilities with a modern web interface. This platform enables semantic search across multiple file types using state-of-the-art ML models, wrapped in a user-friendly interface with modularity and scalability.

![Image 1](description-images/1.png)
![Image 2](description-images/2.png)
![Image 3](description-images/3.png)
![Image 4](description-images/4.png)
![Image 5](description-images/5.png)

## 🌟 System Overview

The platform consists of two main microservices:

### Vector Search Service (Python)

- Advanced semantic search engine
- Multi-modal search capabilities (text & images)
- Multiple file format processing (ZIP, RAR archives, PDF documents, TXT files and images)
- High-performance vector database (Milvus)
- Neural processing with CLIP & Sentence Transformers

### Web Application (Next.js)

- Secure authentication and authorization with OAuth
- LLM integration
- High-performance gRPC communication
- Database management
- Modern UI with Ant Design

## ✨ Key Features

- **Intelligent Search**

  - 🔍 Semantic search across documents and images
  - 📄 Support for multiple file formats (PDF, TXT, Images, Archives)
  - 🤖 State-of-the-art ML models for understanding content
  - ⚡ High-performance vector similarity search

- **Modern Web Interface**
  - 🎨 Intuitive, responsive design
  - 🔐 Secure OAuth authentication
  - 🔄 Context-based LLM itnegration

## 🏗️ Architecture

The platform follows a microservices architecture with clean separation of concerns:

### System Components

1. **Frontend (Next.js)**

   - App Router for routing
   - Ant Design components
   - Server-side rendering
   - SEO optimization

2. **Backend API (Next.js)**

   - API routes
   - MySQL with Prisma ORM

3. **Vector Search Service (Python)**

   - File processing pipeline
   - Embedding generation
   - Vector storage and retrieval
   - gRPC/REST APIs

4. **Databases**
   - MySQL for application data
   - Milvus for vector storage

### Communication Flow

1. User signs in → Web App
2. User uploads files → Web App
3. Web App processes request → Vector Service
4. Vector Service generates embeddings → Milvus
5. Search queries flow through similar pipeline
6. Results aggregated, constructed into context prompt for LLM
7. User gets relevant response regarding their documents

---

Built with ❤️ using Next.js, Python, and cutting-edge ML models
