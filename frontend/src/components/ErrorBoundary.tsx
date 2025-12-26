/**
 * Error Boundary Component
 * Catches and handles React errors gracefully
 */
import { Component, ErrorInfo, ReactNode } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  Button,
  VStack,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Code,
} from '@chakra-ui/react';
import { FiRefreshCw, FiHome } from 'react-icons/fi';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(_error: Error): Partial<ErrorBoundaryState> {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log the error to console for debugging
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Update state with error details
    this.setState({
      error: error,
      errorInfo: errorInfo,
    });

    // You could also log to an error reporting service here
    // e.g., Sentry, LogRocket, etc.
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleGoHome = (): void => {
    window.location.href = '/';
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Fallback UI
      return (
        <Container maxW="container.lg" py={16}>
          <VStack spacing={8} align="stretch">
            <Alert
              status="error"
              variant="subtle"
              flexDirection="column"
              alignItems="center"
              justifyContent="center"
              textAlign="center"
              minHeight="200px"
              borderRadius="md"
            >
              <AlertIcon boxSize="40px" mr={0} />
              <AlertTitle mt={4} mb={1} fontSize="2xl">
                Something went wrong
              </AlertTitle>
              <AlertDescription maxWidth="lg" mt={2}>
                {this.state.error && (
                  <Text fontSize="md" mb={4}>
                    {this.state.error.toString()}
                  </Text>
                )}
                <Text fontSize="sm" color="gray.600">
                  The application encountered an unexpected error. This has been logged and
                  we'll look into it.
                </Text>
              </AlertDescription>
            </Alert>

            <VStack spacing={4}>
              <Button
                leftIcon={<FiRefreshCw />}
                colorScheme="blue"
                size="lg"
                onClick={this.handleReset}
              >
                Try Again
              </Button>
              <Button
                leftIcon={<FiHome />}
                variant="outline"
                size="lg"
                onClick={this.handleGoHome}
              >
                Go to Home
              </Button>
            </VStack>

            {import.meta.env.DEV && this.state.errorInfo && (
              <Box
                bg="gray.50"
                p={4}
                borderRadius="md"
                maxH="400px"
                overflowY="auto"
              >
                <Heading size="sm" mb={3}>
                  Error Details (Development Only)
                </Heading>
                <Code display="block" whiteSpace="pre" fontSize="xs" p={3} borderRadius="md">
                  {this.state.errorInfo.componentStack}
                </Code>
              </Box>
            )}
          </VStack>
        </Container>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
