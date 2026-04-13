/**
 * SecondBrain Auth Logic
 * Connects to FastAPI backend
 */

const API_BASE = "http://localhost:8002"; // Adjust if your backend runs on a different port

document.addEventListener('DOMContentLoaded', () => {
    const loginView = document.getElementById('login-view');
    const signupView = document.getElementById('signup-view');
    const showSignup = document.getElementById('show-signup');
    const showLogin = document.getElementById('show-login');

    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');

    // Toggle between Login and Signup
    showSignup.addEventListener('click', (e) => {
        e.preventDefault();
        loginView.style.display = 'none';
        signupView.style.display = 'block';
    });

    showLogin.addEventListener('click', (e) => {
        e.preventDefault();
        signupView.style.display = 'none';
        loginView.style.display = 'block';
    });

    // Handle Login
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const btn = document.getElementById('login-btn');

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Authenticating...';

        try {
            const response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('sb_token', data.access_token);
                localStorage.setItem('sb_username', username);
                window.location.href = 'index.html';
            } else {
                alert(data.detail || 'Access Denied');
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('Could not connect to the neural core. Please check if the backend is running.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = 'Initialize Session';
        }
    });

    // Handle Signup
    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('reg-username').value;
        const password = document.getElementById('reg-password').value;
        const btn = document.getElementById('signup-btn');

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deploying...';

        try {
            const response = await fetch(`${API_BASE}/auth/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                alert('Instance deployed successfully! Please log in.');
                showLogin.click();
            } else {
                alert(data.detail || 'Deployment failed');
            }
        } catch (error) {
            console.error('Signup error:', error);
            alert('Could not connect to the neural core.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = 'Deploy Instance';
        }
    });
});
