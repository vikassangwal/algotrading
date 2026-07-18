import React, { useState } from 'react';

const AuthViews = ({ setToken }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [errors, setErrors] = useState({});

  const validate = () => {
    const newErrors = {};
    if (!email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = 'Email address is invalid';
    }
    
    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }

    if (!isLogin && !name) {
      newErrors.name = 'Name is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (validate()) {
      try {
        const endpoint = isLogin ? '/login' : '/api/auth/register';
        const payload = isLogin 
          ? { password: password } 
          : { email, password, role: "user" }; // Dummy role
        
        // Use standard JSON for login since main.py expects JSON LoginRequest
        const body = isLogin 
          ? JSON.stringify(payload)
          : JSON.stringify(payload);
          
        const headers = { 'Content-Type': 'application/json' };

        const res = await fetch(`${import.meta.env.VITE_API_URL || ""}${endpoint}`, {
          method: 'POST',
          headers: headers,
          body: body
        });
        
        const data = await res.json();
        
        if (res.ok) {
          if (data.token) {
            localStorage.setItem('elco_token', data.token);
            if (setToken) setToken(data.token);
          }
        } else {
          setErrors({ form: data.detail || 'Authentication failed' });
        }
      } catch (err) {
        setErrors({ form: 'Server error. Is the backend running?' });
      }
    }
  };

  return (
    <>
      <style>{`
        .auth-container {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
          font-family: 'Inter', 'Roboto', sans-serif;
          padding: 20px;
          box-sizing: border-box;
        }
        .glass-card {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border-radius: 24px;
          border: 1px solid rgba(255, 255, 255, 0.2);
          padding: 40px;
          width: 100%;
          max-width: 420px;
          box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
          color: #ffffff;
        }
        .glass-card h2 {
          margin: 0 0 30px 0;
          font-size: 32px;
          font-weight: 700;
          text-align: center;
          letter-spacing: 0.5px;
        }
        .form-group {
          display: flex;
          flex-direction: column;
          margin-bottom: 20px;
        }
        .form-group label {
          font-size: 14px;
          font-weight: 500;
          margin-bottom: 8px;
          color: rgba(255, 255, 255, 0.9);
        }
        .form-group input {
          padding: 14px 16px;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.2);
          background: rgba(255, 255, 255, 0.08);
          color: #ffffff;
          font-size: 16px;
          outline: none;
          transition: all 0.3s ease;
        }
        .form-group input::placeholder {
          color: rgba(255, 255, 255, 0.5);
        }
        .form-group input:focus {
          border-color: rgba(255, 255, 255, 0.5);
          background: rgba(255, 255, 255, 0.15);
        }
        .error-text {
          color: #ff8787;
          font-size: 13px;
          margin-top: 6px;
        }
        .submit-btn {
          width: 100%;
          padding: 16px;
          border-radius: 12px;
          border: none;
          background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
          color: #ffffff;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          margin-top: 10px;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
          box-shadow: 0 4px 15px rgba(79, 172, 254, 0.4);
        }
        .submit-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(79, 172, 254, 0.6);
        }
        .submit-btn:active {
          transform: translateY(0);
        }
        .switch-text {
          margin-top: 30px;
          text-align: center;
          font-size: 14px;
          color: rgba(255, 255, 255, 0.7);
        }
        .switch-text span {
          color: #00f2fe;
          font-weight: 600;
          cursor: pointer;
          transition: color 0.3s ease;
        }
        .switch-text span:hover {
          color: #ffffff;
        }
      `}</style>
      <div className="auth-container">
        <div className="glass-card">
          <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
          
          <form className="auth-form" onSubmit={handleSubmit}>
            {errors.form && <div style={{color: '#ef4444', marginBottom: '10px', fontSize: '14px', textAlign: 'center'}}>{errors.form}</div>}
            {!isLogin && (
              <div className="form-group">
                <label>Full Name</label>
                <input 
                  type="text" 
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="John Doe"
                />
                {errors.name && <span className="error-text">{errors.name}</span>}
              </div>
            )}

            <div className="form-group">
              <label>Email Address</label>
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
              {errors.email && <span className="error-text">{errors.email}</span>}
            </div>

            <div className="form-group">
              <label>Password</label>
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="•••••••••"
              />
              {errors.password && <span className="error-text">{errors.password}</span>}
            </div>

            <button type="submit" className="submit-btn">
              {isLogin ? 'Sign In' : 'Sign Up'}
            </button>
          </form>

          <p className="switch-text">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <span onClick={() => { setIsLogin(!isLogin); setErrors({}); }}>
              {isLogin ? 'Register now' : 'Log in instead'}
            </span>
          </p>
        </div>
      </div>
    </>
  );
};

export default AuthViews;
