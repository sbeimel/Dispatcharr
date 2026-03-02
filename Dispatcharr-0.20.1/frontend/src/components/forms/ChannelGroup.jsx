// Modal.js
import React from 'react';
import API from '../../api';
import { Flex, TextInput, Button, Modal, Alert } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { isNotEmpty, useForm } from '@mantine/form';
import useChannelsStore from '../../store/channels';

const ChannelGroup = ({ channelGroup = null, isOpen, onClose }) => {
  const canEditChannelGroup = useChannelsStore((s) => s.canEditChannelGroup);

  // Check if editing is allowed
  const canEdit = !channelGroup || canEditChannelGroup(channelGroup.id);

  const form = useForm({
    mode: 'uncontrolled',
    initialValues: {
      name: channelGroup ? channelGroup.name : '',
    },

    validate: {
      name: isNotEmpty('Specify a name'),
    },
  });

  const onSubmit = async () => {
    // Prevent submission if editing is not allowed
    if (channelGroup && !canEdit) {
      notifications.show({
        title: 'Error',
        message: 'Cannot edit group with M3U account associations',
        color: 'red',
      });
      return;
    }

    const values = form.getValues();
    let newGroup;

    if (channelGroup) {
      newGroup = await API.updateChannelGroup({
        id: channelGroup.id,
        ...values,
      });
    } else {
      newGroup = await API.addChannelGroup(values);
    }

    form.reset();
    onClose(newGroup); // Pass the new/updated group back to parent
  };

  if (!isOpen) {
    return <></>;
  }

  return (
    <Modal opened={isOpen} onClose={onClose} title="Channel Group">
      {channelGroup && !canEdit && (
        <Alert color="yellow" mb="md">
          This group cannot be edited because it has M3U account associations.
        </Alert>
      )}
      <form onSubmit={form.onSubmit(onSubmit)}>
        <TextInput
          id="name"
          name="name"
          label="Name"
          disabled={channelGroup && !canEdit}
          {...form.getInputProps('name')}
          key={form.key('name')}
        />

        <Flex mih={50} gap="xs" justify="flex-end" align="flex-end">
          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={form.submitting || (channelGroup && !canEdit)}
            size="small"
          >
            Submit
          </Button>
        </Flex>
      </form>
    </Modal>
  );
};

export default ChannelGroup;
