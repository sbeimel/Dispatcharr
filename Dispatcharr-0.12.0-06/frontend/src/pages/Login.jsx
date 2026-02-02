import React from 'react';
import LoginForm from '../components/forms/LoginForm';
import SuperuserForm from '../components/forms/SuperuserForm';
import useAuthStore from '../store/auth';

const Login = ({}) => {
  const superuserExists = useAuthStore((s) => s.superuserExists);

  if (!superuserExists) {
    return <SuperuserForm />;
  }

  return <LoginForm />;
};

export default Login;
