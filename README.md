# 🤖 AI Study Planner Agent (Flask + LangGraph + Groq + ChromaDB)

An **Agentic AI Study Planner Web App** that generates a **day-wise study plan** using your **Syllabus PDF** (RAG) and answers doubts via an AI chatbot.


✅ Upload Syllabus PDF  

✅ Generate Day-wise Study Plan (RAG based)  

✅ Daily Goal Mode (3 topics mandatory)  

✅ Suggest Next Topic  

✅ RAG Chatbot (Ask: "Why this topic got 4 hours?")  

✅ Mark Done / Delete Task / Delete All Plans  

✅ SQLite database storage  

✅ Colorful modern UI

---

## 🚀 Tech Stack

- **Backend:** Flask

- **Agent Workflow:** LangGraph

- **LLM:** Groq (Llama 3)

- **RAG Vector DB:** ChromaDB

- **Database:** SQLite

- **PDF Reader:** PyPDF


---
Setup (Normal pip method)
✅ 1) Clone the project:

      git clone <rarihant14>
      cd ai_study_planner

✅ 2) Install dependencies
        
        pip install -r requirements.txt

✅ 3) Create .env file
Create a file named .env in root folder:

      GROQ_API_KEY=your_groq_api_key_here

✅ 4) Run the app
          
            python app.py
      





