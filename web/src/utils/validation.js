export const validateUsername = (username) => {
  if (!username || username.trim() === '') {
    return 'Username is required';
  }
  if (username.length < 3) {
    return 'Username must be at least 3 characters';
  }
  if (username.length > 30) {
    return 'Username must be under 30 characters';
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    return 'Username can only contain letters, numbers, and underscores';
  }
  return null;
};

export const validatePassword = (password, isLogin = true) => {
  if (!password || password === '') {
    return 'Password is required';
  }
  if (!isLogin && password.length < 8) {
    return 'Password must be at least 8 characters';
  }
  return null;
};

export const validateAuthForm = (username, password, isLogin) => {
  const errors = {};
  const usernameError = validateUsername(username);
  const passwordError = validatePassword(password, isLogin);
  if (usernameError) errors.username = usernameError;
  if (passwordError) errors.password = passwordError;
  return errors;
};