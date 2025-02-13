from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import bcrypt
import torch
import torch.nn as nn
import numpy as np
import logging
import os
from sklearn.preprocessing import StandardScaler
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 配置日志记录
def setup_logging():
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('app.log')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.DEBUG)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

# 模型配置
MODEL_CONFIGS = {
    'type1': {
        'name': 'Co-flow',
        'input_dim': 8,
        'model_path': 'module/mlp_model_Co-flow.pth',
        'train_file': 'train_file/Diameter-C-train.xlsx',
        'features': ['D1', 'D2', 'D3', 'Q1', 'Q2', 's', 'μ1', 'μ2']
    },
    'type2': {
        'name': 'T-junction',
        'input_dim': 8,
        'model_path': 'module/mlp_model_T-junction.pth',
        'train_file': 'train_file/Diameter-T-train.xlsx',
        'features': ['X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8']
    },
    'type3': {
        'name': 'Flow-focusing',
        'input_dim': 9,
        'model_path': 'module/mlp_model_Flow-focusing.pth',
        'train_file': 'train_file/Diameter-F-train.xlsx',
        'features': ['X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9']
    }
}

class MLP(nn.Module):
    def __init__(self, input_dim: int):
        super(MLP, self).__init__()
        self.fc1 = nn.Linear(input_dim, 100)
        self.fc2 = nn.Linear(100, 100)
        self.fc3 = nn.Linear(100, 1)

        for layer in [self.fc1, self.fc2, self.fc3]:
            torch.nn.init.xavier_uniform_(layer.weight)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class ModelManager:
    def __init__(self):
        self.scalers: Dict[str, StandardScaler] = {}
        self.models: Dict[str, MLP] = {}

    def load_model(self, model_type: str) -> Optional[Tuple[MLP, StandardScaler]]:
        if model_type not in MODEL_CONFIGS:
            raise ValueError(f"Invalid model type: {model_type}")

        if model_type not in self.models:
            config = MODEL_CONFIGS[model_type]

            scaler = StandardScaler()
            try:
                train_data = pd.read_excel(config['train_file'])
                X_train = train_data[config['features']].values
                scaler.fit(X_train)
                self.scalers[model_type] = scaler
            except Exception as e:
                app.logger.error(f"Failed to fit scaler for {config['name']}: {str(e)}")
                raise

            try:
                model = MLP(config['input_dim'])
                model.load_state_dict(torch.load(config['model_path'], map_location=torch.device('cpu')))
                model.eval()
                self.models[model_type] = model
            except Exception as e:
                app.logger.error(f"Failed to load model for {config['name']}: {str(e)}")
                raise

        return self.models[model_type], self.scalers[model_type]

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    history = db.relationship('PredictionHistory', backref='user', lazy=True)

# 预测历史记录模型
class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_type = db.Column(db.String(50), nullable=False)
    input_data = db.Column(db.String(255), nullable=False)
    prediction = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 初始化模型管理器
model_manager = ModelManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在，请选择其他用户名。', 'danger')
            return redirect(url_for('register'))

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = User(username=username, password=hashed)
        db.session.add(new_user)
        db.session.commit()

        flash('注册成功，请登录。', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.checkpw(password.encode('utf-8'), user.password):
            login_user(user)
            flash('登录成功。', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误。', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录。', 'success')
    return redirect(url_for('index'))

@app.route('/history')
@login_required
def history():
    history = PredictionHistory.query.filter_by(user_id=current_user.id).all()
    return render_template('history.html', history=history)

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400

        data_type = data.get('dataType')
        if data_type not in MODEL_CONFIGS:
            return jsonify({'error': f'Invalid data type: {data_type}'}), 400

        input_data = np.array(data.get('inputData')).reshape(1, -1)

        if not isinstance(input_data, np.ndarray) or input_data.shape[1] != MODEL_CONFIGS[data_type]['input_dim']:
            return jsonify({'error': 'Invalid input dimensions'}), 400

        if np.isnan(input_data).any() or np.isinf(input_data).any():
            return jsonify({'error': 'Input contains invalid values (NaN or inf)'}), 400

        model, scaler = model_manager.load_model(data_type)

        input_scaled = scaler.transform(input_data)
        input_tensor = torch.tensor(input_scaled, dtype=torch.float32)

        with torch.no_grad():
            output = model(input_tensor)
            prediction = output.item()

        if np.isnan(prediction):
            raise ValueError("Model produced NaN prediction")

        # 保存预测历史记录
        history_record = PredictionHistory(
            user_id=current_user.id,
            data_type=data_type,
            input_data=str(data.get('inputData')),
            prediction=prediction
        )
        db.session.add(history_record)
        db.session.commit()

        app.logger.info(f"Successful prediction for {MODEL_CONFIGS[data_type]['name']}: {prediction}")
        return jsonify({'prediction': prediction})

    except Exception as e:
        app.logger.error(f"Prediction error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    os.makedirs('module', exist_ok=True)
    os.makedirs('train_file', exist_ok=True)

    setup_logging()

    with app.app_context():
        db.create_all()

    app.run(debug=True, host='0.0.0.0', port=5000)