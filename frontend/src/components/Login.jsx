import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import api from '../api';

function getLoginError(error) {
  const data = error.response?.data;
  if (typeof data === 'string') return data;
  if (data?.detail) return data.detail;
  if (data?.non_field_errors?.length) return data.non_field_errors.join(' ');
  if (data && typeof data === 'object') {
    return Object.values(data).flat().filter(Boolean).join(' ');
  }
  return error.message || 'Unable to sign in. Please try again.';
}

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const location = useLocation();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const response = await api.post('/auth/login/', { email, password });
      const accessToken = response.data?.tokens?.access;
      if (!accessToken || !response.data?.user) {
        throw new Error('The login service returned an incomplete response.');
      }
      localStorage.setItem('token', accessToken);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      const destination = location.state?.from?.pathname || '/';
      window.location.assign(destination);
    } catch (loginError) {
      setError(getLoginError(loginError));
      setSubmitting(false);
    }
  };

  return (
    <section className="auth-page" aria-labelledby="login-heading">
      <form className="auth-card" onSubmit={handleSubmit}>
        <p className="eyebrow">Welcome back</p>
        <h1 id="login-heading">Sign in to EventEase</h1>
        <label htmlFor="login-email">Email</label>
        <input
          id="login-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
        <p>New to EventEase? <Link to="/register">Create a customer account</Link></p>
        <Link to="/" className="auth-home-link">Return to events</Link>
      </form>
    </section>
  );
}

export default Login;
