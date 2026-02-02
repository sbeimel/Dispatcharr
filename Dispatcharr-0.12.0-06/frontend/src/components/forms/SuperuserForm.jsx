// frontend/src/components/forms/SuperuserForm.js
import React, { useState } from 'react';
import { TextInput, Center, Button, Paper, Title, Stack } from '@mantine/core';
import API from '../../api';
import useAuthStore from '../../store/auth';

function SuperuserForm() {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
  });
  const [error, setError] = useState('');
  const setSuperuserExists = useAuthStore((s) => s.setSuperuserExists);

  const handleChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      console.log(formData);
      const response = await API.createSuperUser({
        username: formData.username,
        password: formData.password,
        email: formData.email,
      });
      if (response.superuser_exists) {
        setSuperuserExists(true);
      }
    } catch (err) {
      console.log(err);
      setError('Failed to create superuser.');
    }
  };

  return (
    <Center
      style={{
        height: '100vh',
      }}
    >
      <Paper
        elevation={3}
        style={{ padding: 30, width: '100%', maxWidth: 400 }}
      >
        <Title order={4} align="center">
          Create your Super User Account
        </Title>
        <form onSubmit={handleSubmit}>
          <Stack>
            <TextInput
              label="Username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
            />
            <TextInput
              label="Password"
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
            />

            <TextInput
              label="Email (optional)"
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
            />

            <Button type="submit" size="sm" sx={{ pt: 1 }}>
              Submit
            </Button>
          </Stack>
        </form>
      </Paper>
    </Center>
  );
}

export default SuperuserForm;
