/**
 * Application Entry Point
 *
 * Sets up React Query, Chakra UI, and renders the root App component.
 */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ChakraProvider } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './index.css';
import App from './App';
import AuthGate from './components/AuthGate';
import theme from './theme';

// Create React Query client with default options
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
});

// Get root element with null check for TypeScript
const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element not found. Make sure there is a div with id="root" in your HTML.');
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={theme}>
        <AuthGate>
          <App />
        </AuthGate>
      </ChakraProvider>
    </QueryClientProvider>
  </StrictMode>
);
