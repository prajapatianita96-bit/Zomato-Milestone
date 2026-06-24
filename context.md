# Context: AI-Powered Restaurant Recommendation System (Zomato Use Case)

## Project Overview

This project involves building an **AI-powered restaurant recommendation service** inspired by Zomato. The system combines structured restaurant data with a Large Language Model (LLM) to provide personalized, human-like restaurant suggestions based on user preferences.

---

## Objective

Design and implement an application that:
- Accepts user preferences (location, budget, cuisine, ratings, etc.)
- Uses a real-world Zomato restaurant dataset
- Leverages an LLM to generate personalized recommendations
- Displays clear, structured, and useful results to the user

---

## Dataset

- **Source**: Hugging Face — [`ManikaSaini/zomato-restaurant-recommendation`](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- **Key Fields Extracted**: Restaurant name, location, cuisine type, cost, rating, and other relevant attributes

---

## System Workflow

### 1. Data Ingestion
- Load and preprocess the Zomato dataset from Hugging Face
- Extract and clean relevant fields: restaurant name, location, cuisine, cost, rating, etc.

### 2. User Input
Collect the following user preferences:
| Preference | Example Values |
|---|---|
| Location | Delhi, Bangalore |
| Budget | Low, Medium, High |
| Cuisine | Italian, Chinese, etc. |
| Minimum Rating | e.g., 4.0 and above |
| Additional Preferences | Family-friendly, quick service, etc. |

### 3. Integration Layer
- Filter restaurant data based on user input
- Structure filtered results into an LLM-compatible prompt
- Design a prompt that enables the LLM to reason and rank options intelligently

### 4. Recommendation Engine (LLM)
The LLM is responsible for:
- **Ranking** restaurants from the filtered dataset
- **Explaining** why each recommendation fits the user's preferences
- **Summarizing** choices (optional)

### 5. Output Display
Present top recommendations in a user-friendly format:
- 🍽️ **Restaurant Name**
- 🍜 **Cuisine**
- ⭐ **Rating**
- 💰 **Estimated Cost**
- 🤖 **AI-generated explanation**

---

## Key Components

| Component | Responsibility |
|---|---|
| Data Loader | Fetch & preprocess the Hugging Face dataset |
| Input Handler | Collect and validate user preferences |
| Filter Engine | Query dataset based on user preferences |
| Prompt Builder | Format filtered data into an LLM prompt |
| LLM Engine | Call LLM API; generate ranked recommendations |
| Output Renderer | Display results in a structured, readable format |

---

## Source Reference

- **Problem Statement File**: [`Problemstatement.txt`](file:///d:/Zomato-Milestone/Docs/Problemstatement.txt)
- **Dataset**: [Zomato Restaurant Recommendation on Hugging Face](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
