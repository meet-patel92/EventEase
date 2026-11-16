import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import api from '../api';

function Register() {
  const [form, setForm] = useState({ username: '', email: '', password: '', password_confirm: '', first_name: '', last_name: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const location = useLocation();

  const update = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const response = await api.post('/auth/register/', form);
      localStorage.setItem('token', response.data.tokens.access);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      const destination = location.state?.from?.pathname || '/';
      window.location.assign(destination);
    } catch (requestError) {
      const data = requestError.response?.data;
      setError(data?.detail || Object.values(data || {}).flat().filter(Boolean).join(' ') || requestError.message || 'Could not create the account.');
      setSubmitting(false);
    }
  };

  return (
    <section className="auth-page" aria-labelledby="register-heading">
      <form className="auth-card" onSubmit={submit}>
        <p className="eyebrow">Join EventEase</p>
        <h1 id="register-heading">Create a customer account</h1>
        {[
          ['username', 'Username', 'text'], ['email', 'Email', 'email'],
          ['first_name', 'First name', 'text'], ['last_name', 'Last name', 'text'],
          ['password', 'Password', 'password'], ['password_confirm', 'Confirm password', 'password'],
        ].map(([name, label, type]) => (
          <label className="auth-field" key={name}>{label}
            <input name={name} type={type} value={form[name]} onChange={update} required minLength={type === 'password' ? 8 : undefined} autoComplete={type === 'password' ? (name === 'password' ? 'new-password' : 'new-password') : undefined} />
          </label>
        ))}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary" disabled={submitting}>{submitting ? 'Creating account…' : 'Create account'}</button>
        <p>Already registered? <Link to="/login">Sign in</Link></p>
      </form>
    </section>
  );
}

export default Register;
