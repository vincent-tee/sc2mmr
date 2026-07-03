/**
 * PageHeader Component
 * Clubhouse editorial header: small kicker line, big left-aligned display
 * title (optional orange accent word), context actions on the right, and a
 * giant faded backdrop word for flair. Replaces the old centered heroes.
 */
import React, { ReactNode } from 'react';
import { Box, Container, Flex, Heading, HStack, Text } from '@chakra-ui/react';

interface PageHeaderStat {
  label: string;
  value: string | number;
}

interface PageHeaderProps {
  /** Small uppercase label above the title, e.g. "SQUAD RECORDS" */
  kicker?: string;
  /** Main title; the part wrapped in [brackets] renders in brand orange */
  title: string;
  /** Supporting line under the title */
  description?: string;
  /** Right-aligned actions (buttons, selects) */
  actions?: ReactNode;
  /** Inline stat chips rendered under the description */
  stats?: PageHeaderStat[];
}

/** Split "Match [Archive]" into segments, accent inside brackets */
const renderAccentedTitle = (title: string): ReactNode => {
  const parts = title.split(/(\[[^\]]+\])/g);
  return parts.map((part, i) =>
    part.startsWith('[') && part.endsWith(']') ? (
      <Text as="span" key={i} color="brand.500">
        {part.slice(1, -1)}
      </Text>
    ) : (
      <React.Fragment key={i}>{part}</React.Fragment>
    )
  );
};

const PageHeader: React.FC<PageHeaderProps> = ({
  kicker,
  title,
  description,
  actions,
  stats,
}) => (
  <Box position="relative" overflow="hidden" borderBottom="1px solid" borderColor="whiteAlpha.100">
    <Container maxW="container.xl" position="relative" zIndex={1}>
      <Flex
        pt={{ base: 6, md: 8 }}
        pb={{ base: 5, md: 6 }}
        align={{ base: 'start', md: 'end' }}
        justify="space-between"
        direction={{ base: 'column', md: 'row' }}
        gap={4}
      >
        <Box>
          {kicker && (
            <HStack spacing={2} mb={1}>
              <Box w="18px" h="3px" bg="brand.500" borderRadius="full" />
              <Text
                fontFamily="mono"
                fontSize="xs"
                fontWeight="600"
                letterSpacing="0.18em"
                textTransform="uppercase"
                color="accent.400"
              >
                {kicker}
              </Text>
            </HStack>
          )}
          <Heading
            as="h1"
            fontSize={{ base: '3xl', md: '5xl' }}
            lineHeight="1.05"
            color="gray.50"
          >
            {renderAccentedTitle(title)}
          </Heading>
          {description && (
            <Text color="gray.500" mt={2} fontSize={{ base: 'sm', md: 'md' }} maxW="560px">
              {description}
            </Text>
          )}
          {stats && stats.length > 0 && (
            <HStack spacing={5} mt={3} flexWrap="wrap">
              {stats.map((stat) => (
                <HStack key={stat.label} spacing={2} align="baseline">
                  <Text fontFamily="mono" fontWeight="700" fontSize="lg" color="gray.100">
                    {stat.value}
                  </Text>
                  <Text fontSize="xs" color="gray.500" textTransform="uppercase" letterSpacing="0.08em">
                    {stat.label}
                  </Text>
                </HStack>
              ))}
            </HStack>
          )}
        </Box>
        {actions && <Box flexShrink={0}>{actions}</Box>}
      </Flex>
    </Container>
  </Box>
);

export default PageHeader;
