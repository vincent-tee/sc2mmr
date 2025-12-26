/**
 * Custom Toast Hook
 * Simplified toast notifications with consistent styling
 */
import { useToast as useChakraToast } from '@chakra-ui/react';

interface ToastMethods {
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
  info: (message: string, title?: string) => void;
}

export const useToast = (): ToastMethods => {
  const toast = useChakraToast();

  return {
    success: (message: string, title = 'Success') => {
      toast({
        title,
        description: message,
        status: 'success',
        duration: 3000,
        isClosable: true,
        position: 'top-right',
      });
    },
    error: (message: string, title = 'Error') => {
      toast({
        title,
        description: message,
        status: 'error',
        duration: 5000,
        isClosable: true,
        position: 'top-right',
      });
    },
    warning: (message: string, title = 'Warning') => {
      toast({
        title,
        description: message,
        status: 'warning',
        duration: 4000,
        isClosable: true,
        position: 'top-right',
      });
    },
    info: (message: string, title = 'Info') => {
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
