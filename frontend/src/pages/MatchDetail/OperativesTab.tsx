/**
 * OperativesTab Component - Players/operatives table view
 */
import {
  Box,
  Card,
  CardBody,
  VStack,
  HStack,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Badge,
  Icon,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiAward, FiArrowUp, FiArrowDown } from 'react-icons/fi';
import type { MatchDetail as MatchDetailType } from '@/types/api';

interface OperativesTabProps {
  matchData: MatchDetailType;
  team1Won: boolean;
}

const OperativesTab: React.FC<OperativesTabProps> = ({
  matchData,
  team1Won,
}) => {
  const winnerBg = 'rgba(72, 187, 120, 0.05)';
  const loserBg = 'rgba(245, 101, 101, 0.05)';
  const borderColor = 'space.900';
  const brandShadow = '3px 3px 0 var(--chakra-colors-space-900)';

  const { players } = matchData;

  // Group players by team
  const team1Players = players.filter((p) => p.team_number === 1);
  const team2Players = players.filter((p) => p.team_number === 2);

  return (
    <VStack spacing={6} align="stretch">
      {/* Team 1 */}
      <Box>
        <HStack mb={4} spacing={3}>
          <Heading
            size="md"
            fontFamily="heading"
            letterSpacing="widest"
            textTransform="uppercase"
            color="shield.400"
          >
            Squad Alpha
          </Heading>
          {team1Won && (
            <Badge
              colorScheme="green"
              variant="solid"
              fontSize="sm"
              px={3}
              py={1}
              borderRadius="md"
              fontFamily="heading"
            >
              <Icon as={FiAward} mr={1} />
              Victory
            </Badge>
          )}
        </HStack>
        <Box
          bg={cardBg}
          borderRadius="xl"
          border="3px solid"
          borderColor={borderColor}
          boxShadow={brandShadow}
          overflow="hidden"
        >
          <Box p={4} bg={team1Won ? winnerBg : loserBg}>
            <TableContainer>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th fontFamily="heading" color="gray.500">Player</Th>
                    <Th fontFamily="heading" color="gray.500">Race</Th>
                    <Th isNumeric fontFamily="heading" color="gray.500">
                      Before
                    </Th>
                    <Th isNumeric fontFamily="heading" color="gray.500">
                      After
                    </Th>
                    <Th isNumeric fontFamily="heading" color="gray.500">
                      Swing
                    </Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {team1Players.map((player, idx) => (
                    <Tr key={idx}>
                      <Td fontWeight="bold" fontFamily="heading" color="gray.100">
                        {player.player_name}
                      </Td>
                      <Td>
                        <Badge size="sm" variant="outline" fontFamily="heading">{player.race}</Badge>
                      </Td>
                      <Td isNumeric color="gray.400" fontFamily="mono">{Math.round(player.mmr_before)}</Td>
                      <Td isNumeric color="gray.200" fontFamily="mono" fontWeight="bold">{Math.round(player.mmr_after)}</Td>
                      <Td isNumeric>
                        <HStack justify="flex-end" spacing={1}>
                          <Icon
                            as={
                              player.mmr_change >= 0
                                ? FiArrowUp
                                : FiArrowDown
                            }
                            color={
                              player.mmr_change >= 0 ? 'green.500' : 'red.500'
                            }
                          />
                          <Text
                            color={
                              player.mmr_change >= 0 ? 'green.500' : 'red.500'
                            }
                            fontWeight="bold"
                            fontFamily="mono"
                          >
                            {Math.abs(Math.round(player.mmr_change))}
                          </Text>
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </TableContainer>
          </Box>
        </Box>
      </Box>

      {/* Team 2 */}
      <Box mt={6}>
        <HStack mb={4} spacing={3}>
          <Heading
            size="md"
            fontFamily="heading"
            letterSpacing="widest"
            textTransform="uppercase"
            color="accent.400"
          >
            Squad Bravo
          </Heading>
          {!team1Won && (
            <Badge
              colorScheme="green"
              variant="solid"
              fontSize="sm"
              px={3}
              py={1}
              borderRadius="md"
              fontFamily="heading"
            >
              <Icon as={FiAward} mr={1} />
              Victory
            </Badge>
          )}
        </HStack>
        <Box
          bg={cardBg}
          borderRadius="xl"
          border="3px solid"
          borderColor={borderColor}
          boxShadow={brandShadow}
          overflow="hidden"
        >
          <Box p={4} bg={!team1Won ? winnerBg : loserBg}>
            <TableContainer>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th fontFamily="heading" color="gray.500">Player</Th>
                    <Th fontFamily="heading" color="gray.500">Race</Th>
                    <Th isNumeric fontFamily="heading" color="gray.500">
                      Before
                    </Th>
                    <Th isNumeric fontFamily="heading" color="gray.500">
                      After
                    </Th>
                    <Th isNumeric fontFamily="heading" color="gray.500">
                      Swing
                    </Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {team2Players.map((player, idx) => (
                    <Tr key={idx}>
                      <Td fontWeight="bold" fontFamily="heading" color="gray.100">
                        {player.player_name}
                      </Td>
                      <Td>
                        <Badge size="sm" variant="outline" fontFamily="heading">{player.race}</Badge>
                      </Td>
                      <Td isNumeric color="gray.400" fontFamily="mono">{Math.round(player.mmr_before)}</Td>
                      <Td isNumeric color="gray.200" fontFamily="mono" fontWeight="bold">{Math.round(player.mmr_after)}</Td>
                      <Td isNumeric>
                        <HStack justify="flex-end" spacing={1}>
                          <Icon
                            as={
                              player.mmr_change >= 0
                                ? FiArrowUp
                                : FiArrowDown
                            }
                            color={
                              player.mmr_change >= 0 ? 'green.500' : 'red.500'
                            }
                          />
                          <Text
                            color={
                              player.mmr_change >= 0 ? 'green.500' : 'red.500'
                            }
                            fontWeight="bold"
                            fontFamily="mono"
                          >
                            {Math.abs(Math.round(player.mmr_change))}
                          </Text>
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </TableContainer>
          </Box>
        </Box>
      </Box>
    </VStack>
  );
};

export default OperativesTab;
