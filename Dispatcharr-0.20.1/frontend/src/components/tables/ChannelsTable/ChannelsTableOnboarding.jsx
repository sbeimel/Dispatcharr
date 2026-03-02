import { Box, Button, Center, Text, useMantineTheme } from '@mantine/core';
import ghostImage from '../../../images/ghost.svg';
import { SquarePlus } from 'lucide-react';

const ChannelsTableOnboarding = ({ editChannel }) => {
  const theme = useMantineTheme();

  return (
    <Box
      style={{
        paddingTop: 20,
        bgcolor: theme.palette.background.paper,
      }}
    >
      <Center>
        <Box
          style={{
            textAlign: 'center',
            width: '55%',
          }}
        >
          <Text
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 400,
              fontSize: '20px',
              lineHeight: '28px',
              letterSpacing: '-0.3px',
              color: theme.palette.text.secondary,
              mb: 1,
            }}
          >
            It’s recommended to create channels after adding your M3U or
            streams.
          </Text>
          <Text
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 400,
              fontSize: '16px',
              lineHeight: '24px',
              letterSpacing: '-0.2px',
              color: theme.palette.text.secondary,
              mb: 2,
            }}
          >
            You can still create channels without streams if you’d like, and map
            them later.
          </Text>
          <Button
            leftSection={<SquarePlus size={18} />}
            variant="light"
            size="xs"
            onClick={() => editChannel()}
            color="gray"
            style={{
              marginTop: 20,
              borderWidth: '1px',
              borderColor: 'gray',
              color: 'white',
            }}
          >
            Create Channel
          </Button>
        </Box>
      </Center>

      <Center>
        <Box
          component="img"
          src={ghostImage}
          alt="Ghost"
          style={{
            paddingTop: 30,
            width: '120px',
            height: 'auto',
            opacity: 0.2,
            pointerEvents: 'none',
          }}
        />
      </Center>
    </Box>
  );
};

export default ChannelsTableOnboarding;
