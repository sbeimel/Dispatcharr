// Modal.js
import React, { useEffect } from 'react';
import { useFormik } from 'formik';
import * as Yup from 'yup';
import API from '../../api';
import {
  LoadingOverlay,
  TextInput,
  Button,
  Checkbox,
  Modal,
  Flex,
  NativeSelect,
  FileInput,
  Space,
} from '@mantine/core';
import { NETWORK_ACCESS_OPTIONS } from '../../constants';

const UserAgent = ({ userAgent = null, isOpen, onClose }) => {
  const formik = useFormik({
    initialValues: {
      name: '',
      user_agent: '',
      description: '',
      is_active: true,
    },
    validationSchema: Yup.object({
      name: Yup.string().required('Name is required'),
      user_agent: Yup.string().required('User-Agent is required'),
    }),
    onSubmit: async (values, { setSubmitting, resetForm }) => {
      if (userAgent?.id) {
        await API.updateUserAgent({ id: userAgent.id, ...values });
      } else {
        await API.addUserAgent(values);
      }

      resetForm();
      setSubmitting(false);
      onClose();
    },
  });

  useEffect(() => {
    if (userAgent) {
      formik.setValues({
        name: userAgent.name,
        user_agent: userAgent.user_agent,
        description: userAgent.description,
        is_active: userAgent.is_active,
      });
    } else {
      formik.resetForm();
    }
  }, [userAgent]);

  if (!isOpen) {
    return <></>;
  }

  return (
    <Modal opened={isOpen} onClose={onClose} title="User-Agent">
      <form onSubmit={formik.handleSubmit}>
        <TextInput
          id="name"
          name="name"
          label="Name"
          value={formik.values.name}
          onChange={formik.handleChange}
          error={formik.touched.name && Boolean(formik.errors.name)}
        />

        <TextInput
          id="user_agent"
          name="user_agent"
          label="User-Agent"
          value={formik.values.user_agent}
          onChange={formik.handleChange}
          error={formik.touched.user_agent && Boolean(formik.errors.user_agent)}
        />

        <TextInput
          id="description"
          name="description"
          label="Description"
          value={formik.values.description}
          onChange={formik.handleChange}
          error={
            formik.touched.description && Boolean(formik.errors.description)
          }
        />

        <Space h="md" />

        <Checkbox
          name="is_active"
          label="Is Active"
          checked={formik.values.is_active}
          onChange={formik.handleChange}
        />

        <Flex mih={50} gap="xs" justify="flex-end" align="flex-end">
          <Button
            size="small"
            type="submit"
            variant="contained"
            disabled={formik.isSubmitting}
          >
            Submit
          </Button>
        </Flex>
      </form>
    </Modal>
  );
};

export default UserAgent;
