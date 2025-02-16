
Create the Virtual Environment
```bash
python3 -m venv venv
```

Activate the Vitual Environment
```bash
source venv/bin/activate
```

Install Dependencies
```bash
pip install flask
pip install flask_sqlalchemy
pip install flask_cors
pip install pymysql
```

Start the App
```bash
flask --app main run
```

Experimental
```
pip freeze > requirements.txt
sudo docker build -t flask-backend .
sudo docker run -d -p 5000:5000 flask-backend
```