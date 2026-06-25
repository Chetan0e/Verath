export const validateUsername = (username) => {
  const trimmedUsername = username?.trim() || "";

  if (!trimmedUsername) {
    return "Username is required";
  }

  if (trimmedUsername.length < 3) {
    return "Username must be at least 3 characters";
  }

  if (trimmedUsername.length > 50) {
    return "Username must be 50 characters or less";
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(trimmedUsername)) {
    return "Username can only contain letters, numbers, underscores, and hyphens";
  }

  return null;
};

export const validatePassword = (password, { isSignup = false } = {}) => {
  if (!password || password.trim() === "") {
    return "Password is required";
  }

  if (isSignup && password.length < 8) {
    return "Password must be at least 8 characters";
  }

  return null;
};

