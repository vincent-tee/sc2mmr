/**
 * Custom Toast Hook
 * Simplified toast notifications with consistent styling
 */
import { useToast as useChakraToast } from '@chakra-ui/react';

export const useToast = () => {
  const toast = useChakraToast();

  return {
    success: (message, title = 'Success') => {
      toast({
        title,
        description: message,
        status: 'success',
        duration: 3000,
        isClosable: true,
        position: 'top-right',
      });
    },
    error: (message, title = 'Error') => {
      toast({
        title,
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
        position: 'top-right',
      });
    },
    warning: (message, title = 'Warning') => {
      toast({
        title,
        description: message,
        status: 'warning',
        duration: 4000,
        isClosable: true,
        position: 'top-right',
      });
    },
    info: (message, title = 'Info') => {
      toast({
        title,
        description: message,
        status: 'info',
        duration: 3000,
        isClosable: true,
        position: 'top-right',
      });
    },
  };
};
