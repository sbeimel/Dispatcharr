import { Button as MantineButton } from '@mantine/core';

const Button = (props) => {
  return (
    <MantineButton
      {...props}
      style={{
        color: 'black',
        // fontWeight: '400',
        backgroundColor: '#14917E',
        '&:hover': {
          backgroundColor: '#14917E',
        },
      }}
    />
  );
};

export default Button;
