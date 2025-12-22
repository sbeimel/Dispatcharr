// frontend/src/components/forms/SuperuserForm.js
import React, { useState, useEffect } from 'react';
import {
  TextInput,
  Center,
  Button,
  Paper,
  Title,
  Stack,
  Text,
  Image,
  Divider,
} from '@mantine/core';
import API from '../../api';
import useAuthStore from '../../store/auth';
import logo from '../../assets/logo.png';

function SuperuserForm() {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
  });
  const [error, setError] = useState('');
  const [version, setVersion] = useState(null);
  const setSuperuserExists = useAuthStore((s) => s.setSuperuserExists);

  useEffect(() => {
    // Fetch version info
    API.getVersion().then((data) => {
      setVersion(data?.version);
    });
  }, []);

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
        style={{
          padding: 30,
          width: '100%',
          maxWidth: 500,
          position: 'relative',
        }}
      >
        <Stack align="center" spacing="lg">
          <Image
            src={logo}
            alt="Dispatcharr Logo"
            width={120}
            height={120}
            fit="contain"
          />
          <Title order={2} align="center">
            Dispatcharr
          </Title>
          <Text size="sm" color="dimmed" align="center">
            Welcome! Create your Super User Account to get started.
          </Text>
          <Divider style={{ width: '100%' }} />
        </Stack>
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

            <Button type="submit" fullWidth>
              Create Account
            </Button>
          </Stack>
        </form>

        {version && (
          <Text
            size="xs"
            color="dimmed"
            style={{
              position: 'absolute',
              bottom: 6,
              right: 30,
            }}
          >
            v{version}
          </Text>
        )}
      </Paper>
    </Center>
  );
}

export default SuperuserForm;
