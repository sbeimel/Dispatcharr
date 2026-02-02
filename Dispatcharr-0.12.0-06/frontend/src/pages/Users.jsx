import React, { useState } from 'react';
import UsersTable from '../components/tables/UsersTable';
import { Box } from '@mantine/core';
import useAuthStore from '../store/auth';
import { USER_LEVELS } from '../constants';

const UsersPage = () => {
  const authUser = useAuthStore((s) => s.user);

  const [selectedUser, setSelectedUser] = useState(null);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [userToDelete, setUserToDelete] = useState(null);

  if (!authUser.id) {
    return <></>;
  }

  const closeUserModal = () => {
    setSelectedUser(null);
    setUserModalOpen(false);
  };
  const editUser = (user) => {
    setSelectedUser(user);
    setUserModalOpen(true);
  };

  const deleteUser = (id) => {
    // Get user details for the confirmation dialog
    const user = users.find((u) => u.id === id);
    setUserToDelete(user);
    setDeleteTarget(id);

    // Skip warning if it's been suppressed
    if (isWarningSuppressed('delete-user')) {
      return executeDeleteUser(id);
    }

    setConfirmDeleteOpen(true);
  };

  const executeDeleteUser = async (id) => {
    await API.deleteUser(id);
    setConfirmDeleteOpen(false);
  };

  return (
    <Box style={{ padding: 10 }}>
      <UsersTable />
    </Box>
  );
};

export default UsersPage;
