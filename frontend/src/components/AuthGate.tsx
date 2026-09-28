/**
 * AuthGate - group-password login gate for the hosted deployment.
 *
 * Asks the backend whether auth is enabled (GET /auth/status): when it is
 * and there's no valid session cookie, renders the squad login screen
 * instead of the app. In local dev auth is disabled server-side, so this
 * renders children immediately. Real enforcement lives in the backend
 * middleware - this component is purely the UX for it.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
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

// 'locked' = hard gate: auth is on, public-read is off, no session at all.
// There's nothing rendered behind it, so the login screen has no cancel
// option. 'open' covers public-read browsing, where a soft `prompt` overlay
// (dismissible) asks for the password only when a write is attempted,
// without unmounting the page the visitor was already looking at.
type GateState = 'checking' | 'locked' | 'open';

/**
 * Auth context so individual pages/actions (upload route, download button)
 * can proactively bounce an unauthenticated visitor to the login screen
 * instead of letting the write silently 401. `authenticated` is only false
 * when we have *confirmed* auth is enabled and no valid session exists -
 * when the backend is unreachable we fail open (authenticated: true) so the
 * server middleware stays the single source of truth.
 */
interface AuthContextValue {
  authEnabled: boolean;
  publicRead: boolean;
  authenticated: boolean;
  /**
   * Show the login screen now (e.g. before an upload or download).
   * `onCancel`, if given, runs when the visitor dismisses the prompt instead
   * of logging in - e.g. a route that's gated on entry (upload) should send
   * them somewhere else, while a gated action on an otherwise-browsable page
   * (download) should just close the prompt and leave them on it.
   */
  requireLogin: (onCancel?: () => void) => void;
  /**
   * Resolves true once the visitor may write: immediately when auth is off or
   * a session exists, otherwise after they sign in through the prompt (false
   * if they cancel). `purpose` completes "Sign in to ..." in the prompt.
   */
  ensureSignedIn: (purpose?: string) => Promise<boolean>;
  /** Like ensureSignedIn, but always prompts - for a write that just got a 401. */
  signIn: (purpose?: string) => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue>({
  authEnabled: false,
  publicRead: true,
  authenticated: true,
  requireLogin: () => {},
  ensureSignedIn: async () => true,
  signIn: async () => true,
});

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = (): AuthContextValue => useContext(AuthContext);

const LoginScreen: React.FC<{
  onSuccess: () => void;
  /** When set, renders a secondary button letting a public-read visitor
   * back out of the password prompt instead of the whole app hard-locking. */
  onCancel?: () => void;
  overlay?: boolean;
  purpose?: string;
}> = ({ onSuccess, onCancel, overlay, purpose }) => {
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
    <Center
      minH="100vh"
      bg={overlay ? 'blackAlpha.700' : 'space.900'}
      px={4}
      {...(overlay
        ? { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 'overlay' }
        : {})}
    >
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
            {purpose ? `Sign in to ${purpose}` : 'Members Only'}
          </Heading>
          <Text fontSize="sm" color="gray.500" mt={2}>
            {purpose
              ? 'Enter the squad password. Your picks stay as they are.'
              : 'Enter the squad password to open the tracker.'}
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
          {purpose ? 'Sign in' : 'Enter'}
        </Button>

        {onCancel && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            color="gray.400"
            onClick={onCancel}
            isDisabled={submitting}
          >
            {purpose ? 'Cancel' : 'Go back'}
          </Button>
        )}
      </VStack>
    </Center>
  );
};

const AuthGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<GateState>('checking');
  const [status, setStatus] = useState<AuthStatus | null>(null);
  // Soft, dismissible password prompt shown over the current page (public-read
  // mode only) when a write is attempted while signed out. Unlike `state ===
  // 'locked'`, this never unmounts the page underneath. `promptCancel` is the
  // per-trigger "Go back" behavior - null means just close the prompt.
  const [prompt, setPrompt] = useState(false);
  const [promptCancel, setPromptCancel] = useState<(() => void) | null>(null);
  const [promptPurpose, setPromptPurpose] = useState<string | undefined>(undefined);
  const waitingForSignIn = useRef<((signedIn: boolean) => void)[]>([]);

  const settleWaiting = (signedIn: boolean) => {
    const waiting = waitingForSignIn.current;
    waitingForSignIn.current = [];
    waiting.forEach((resolve) => resolve(signedIn));
  };

  const checkStatus = useCallback(async () => {
    try {
      const { data } = await apiClient.get<AuthStatus>('/auth/status');
      setStatus(data);
      // In public-read mode anonymous browsing is fine - the gate only
      // appears when a write gets a 401 (AUTH_EXPIRED_EVENT below) or a
      // page/action calls requireLogin().
      setState(
        !data.auth_enabled || data.public_read || data.authenticated
          ? 'open'
          : 'locked'
      );
    } catch {
      // Backend unreachable or errored: fail open. The middleware still
      // enforces auth server-side; pages will surface their own errors.
      setStatus(null);
      setState('open');
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  // Session expired mid-use (any API call got a 401): in public-read mode
  // browsing is still fine, so just surface the dismissible prompt; only
  // hard-lock the whole app when public-read is off (nothing was safe to
  // keep showing in the first place).
  useEffect(() => {
    const onExpired = () => {
      if (status?.public_read) {
        setPromptCancel(null);
        setPromptPurpose(undefined);
        setPrompt(true);
      } else {
        setState('locked');
      }
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, [status]);

  const signIn = useCallback((purpose?: string) => {
    setPromptCancel(null);
    setPromptPurpose(purpose);
    setPrompt(true);
    return new Promise<boolean>((resolve) => {
      waitingForSignIn.current.push(resolve);
    });
  }, []);

  const contextValue = useMemo<AuthContextValue>(() => {
    // Fail open when we couldn't confirm status: only block on a *known*
    // unauthenticated session.
    const authenticated = status ? status.authenticated : true;
    const authEnabled = status?.auth_enabled ?? false;
    return {
      authEnabled,
      publicRead: status?.public_read ?? true,
      authenticated,
      requireLogin: (onCancel) => {
        setPromptCancel(() => onCancel ?? null);
        setPromptPurpose(undefined);
        setPrompt(true);
      },
      ensureSignedIn: (purpose) =>
        !authEnabled || authenticated ? Promise.resolve(true) : signIn(purpose),
      signIn,
    };
  }, [status, signIn]);

  const completeSignIn = async () => {
    await checkStatus();
    setPrompt(false);
    setPromptCancel(null);
    settleWaiting(true);
  };

  if (state === 'checking') {
    return (
      <Center minH="100vh" bg="space.900">
        <Spinner size="xl" color="brand.500" thickness="4px" emptyColor="gray.700" />
      </Center>
    );
  }

  // On successful login, re-fetch status (the cookie is now set, so
  // /auth/status returns authenticated: true) rather than merely flipping
  // the gate open - otherwise a route guarded on `authenticated` would see
  // it still false and re-lock in a loop.
  if (state === 'locked') {
    return <LoginScreen onSuccess={completeSignIn} />;
  }

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
      {prompt && (
        <LoginScreen
          overlay
          purpose={promptPurpose}
          onSuccess={completeSignIn}
          onCancel={() => {
            setPrompt(false);
            promptCancel?.();
            setPromptCancel(null);
            settleWaiting(false);
          }}
        />
      )}
    </AuthContext.Provider>
  );
};

export default AuthGate;
