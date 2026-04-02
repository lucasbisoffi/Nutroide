## Nutroide — AI-Powered Nutritional


1. Description
    
    Nutroide is a full-stack web aplication that can help you understand what you actually ate in a day. Throught artifical intelligence, the app show and register the macronutrients of each meal.
    
2. Key Features
    
    
    - Nutroide accepts natural language, which is perfect for users that only know the food’s name, but nothing about your nutritional informations.
    - The dashboard is updated in real-time, without requiring a page refresh, by using asynchronous JavaScript (Fetch API).
    - All data is storage in a structured SQLite database, ensuring meal history.
3. Technical Stack & Design Choices
    
    ---
    
    - The main utility of Nutroide is to calculate macronutrients and to do that, a simple backend in Python (Flask) using a Google Gemini API and JSON manipulation is enought.
    - The frontend was made with Bootstrap to deliever a responsive experience for the user.
    - Instead of a simple table, I designed a relational schema with a one-to-many relationship between meals and individual food items
4. How to run
    
    ---
    
    1. download all the files
    2. open terminal in the repository folder
    3. create and activate a virtual enviroment
        
        ```python
        python3 -m venv venv
        source venv/bin/activate 
        ```
        
    4. install required dependencies  
        
        ```python
        pip install -r requirements.txt
        ```
        
    5. create a .env file and add your GEMINI_API_KEY and FLASK_SECRET_KEY
    6. initialize database
        
        ```python
        sqlite3 nutroide.db < database.sql
        ```
        
    7. run the app
        
        ```python
        python app.py
        ```
        
    8. access the local server at http://127.0.0.1:5000 in your browser.
