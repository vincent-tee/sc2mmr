/**
 * AuthGate - group-password login gate for the hosted deployment.
 *
 * Asks the backend whether auth is enabled (GET /auth/status): when it is
 * and there's no valid session cookie, renders the squad login screen
 * instead of the app. In local dev auth is disabled server-side, so this
 * renders children immediately. Real enforcement lives in the backend
 * middleware - this component is purely the UX for it.
 */
import { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Button,
  Center,
  Heading,
  Input,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react';
import apiClient, { AUTH_EXPIRED_EVENT, ApiClientError } from '../api/client';

interface AuthStatus {
  auth_enabled: boolean;
  /** Anonymous GETs allowed; only writes (uploads etc.) need the session. */
  public_read?: boolean;
  authenticated: boolean;
}

type GateState = 'checking' | 'locked' | 'open';

const LoginScreen: React.FC<{ onSuccess: () => void }> = ({ onSuccess }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiClient.post('/auth/login', { password });
      onSuccess();
    } catch (err) {
      const apiError = err as ApiClientError;
      if (apiError.response?.status === 401) {
        setError('Wrong password - ask the squad.');
      } else {
        setError(apiError.userMessage || 'Login failed - try again.');
      }
      setSubmitting(false);
    }
  };

  return (
    <Center minH="100vh" bg="space.900" px={4}>
      <VStack
        as="form"
        onSubmit={handleSubmit}
        spacing={6}
        bg="space.800"
        border="1px solid"
        borderColor="space.700"
        borderRadius="xl"
        p={{ base: 8, md: 12 }}
        maxW="420px"
        w="100%"
        align="stretch"
      >
        <Box>
          <Text
            fontSize="xs"
            fontFamily="mono"
            fontWeight="bold"
            letterSpacing="0.2em"
            textTransform="uppercase"
            color="brand.400"
            mb={2}
          >
            Squad Access
          </Text>
          <Heading size="lg" fontFamily="heading" color="gray.100">
            Members Only
          </Heading>
          <Text fontSize="sm" color="gray.500" mt={2}>
            Enter the squad password to open the tracker.
          </Text>
        </Box>

        <Input
          type="password"
          autoFocus
          placeholder="Squad password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          bg="space.900"
          borderColor="space.700"
          _hover={{ borderColor: 'space.600' }}
          _focus={{ borderColor: 'brand.400', boxShadow: 'none' }}
          size="lg"
          aria-label="Squad password"
        />

        {error && (
          <Text fontSize="sm" color="red.400" role="alert">
            {error}
          </Text>
        )}

        <Button
          type="submit"
          colorScheme="brand"
          size="lg"
          isLoading={submitting}
          isDisabled={!password}
          fontFamily="heading"
          fontWeight="bold"
          letterSpacing="wider"
        >
          Enter
        </Button>
      </VStack>
    </Center>
  );
};

const AuthGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<GateState>('checking');

  const checkStatus = useCallback(async () => {
    try {
      const { data } = await apiClient.get<AuthStatus>('/auth/status');
      // In public-read mode anonymous browsing is fine - the gate only
      // appears when a write gets a 401 (AUTH_EXPIRED_EVENT below).
      setState(
        !data.auth_enabled || data.public_read || data.authenticated
          ? 'open'
          : 'locked'
      );
    } catch {
      // Backend unreachable or errored: fail open. The middleware still
      // enforces auth server-side; pages will surface their own errors.
      setState('open');
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  // Session expired mid-use (any API call got a 401): drop back to login.
  useEffect(() => {
    const onExpired = () => setState('locked');
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, []);

  if (state === 'checking') {
    return (
      <Center minH="100vh" bg="space.900">
        <Spinner size="xl" color="brand.500" thickness="4px" emptyColor="gray.700" />
      </Center>
    );
  }

  if (state === 'locked') {
    return <LoginScreen onSuccess={() => setState('open')} />;
  }

  return <>{children}</>;
};

export default AuthGate;
