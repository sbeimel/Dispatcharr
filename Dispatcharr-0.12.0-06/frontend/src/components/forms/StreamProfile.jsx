// Modal.js
import React, { useEffect } from 'react';
import { useFormik } from 'formik';
import * as Yup from 'yup';
import API from '../../api';
import useUserAgentsStore from '../../store/userAgents';
import { Modal, TextInput, Select, Button, Flex } from '@mantine/core';

const StreamProfile = ({ profile = null, isOpen, onClose }) => {
  const userAgents = useUserAgentsStore((state) => state.userAgents);

  const formik = useFormik({
    initialValues: {
      name: '',
      command: '',
      parameters: '',
      is_active: true,
      user_agent: '',
    },
    validationSchema: Yup.object({
      name: Yup.string().required('Name is required'),
      command: Yup.string().required('Command is required'),
      parameters: Yup.string().required('Parameters are is required'),
    }),
    onSubmit: async (values, { setSubmitting, resetForm }) => {
      if (profile?.id) {
        await API.updateStreamProfile({ id: profile.id, ...values });
      } else {
        await API.addStreamProfile(values);
      }

      resetForm();
      setSubmitting(false);
      onClose();
    },
  });

  useEffect(() => {
    if (profile) {
      formik.setValues({
        name: profile.name,
        command: profile.command,
        parameters: profile.parameters,
        is_active: profile.is_active,
        user_agent: profile.user_agent,
      });
    } else {
      formik.resetForm();
    }
  }, [profile]);

  if (!isOpen) {
    return <></>;
  }

  return (
    <Modal opened={isOpen} onClose={onClose} title="Stream Profile">
      <form onSubmit={formik.handleSubmit}>
        <TextInput
          id="name"
          name="name"
          label="Name"
          value={formik.values.name}
          onChange={formik.handleChange}
          error={formik.errors.name}
          disabled={profile ? profile.locked : false}
        />
        <TextInput
          id="command"
          name="command"
          label="Command"
          value={formik.values.command}
          onChange={formik.handleChange}
          error={formik.errors.command}
          disabled={profile ? profile.locked : false}
        />
        <TextInput
          id="parameters"
          name="parameters"
          label="Parameters"
          value={formik.values.parameters}
          onChange={formik.handleChange}
          error={formik.errors.parameters}
          disabled={profile ? profile.locked : false}
        />

        <Select
          id="user_agent"
          name="user_agent"
          label="User-Agent"
          value={formik.values.user_agent}
          onChange={formik.handleChange}
          error={formik.errors.user_agent}
          data={userAgents.map((ua) => ({
            label: ua.name,
            value: `${ua.id}`,
          }))}
        />

        <Flex mih={50} gap="xs" justify="flex-end" align="flex-end">
          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={formik.isSubmitting}
            size="small"
          >
            Submit
          </Button>
        </Flex>
      </form>
    </Modal>
  );
};

export default StreamProfile;
