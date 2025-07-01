import { useParams, useHistory } from 'react-router-dom';
import { useState } from 'react';

const ResetChangePassword = () => {
  const { uid, token } = useParams();
  const history = useHistory();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();

    fetch(`${process.env.REACT_APP_API_URL || ''}/api/auth/password/reset/confirm/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        uid,
        token,
        new_password: password,
      }),
    })
      .then((res) => {
        if (!res.ok) {
          return res.json().then((err) => Promise.reject(err));
        }
        history.push('/signin');
      })
      .catch((err) => {
        const errors = Object.values(err);
        setError(errors.join(', '));
      });
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Введите новый пароль</h2>
      <input
        type="password"
        placeholder="Новый пароль"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button type="submit">Сменить пароль</button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </form>
  );
};

export default ResetChangePassword;
