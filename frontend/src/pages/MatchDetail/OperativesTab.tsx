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
  const winnerBg = useColorModeValue('green.50', 'rgba(0, 255, 136, 0.1)');
  const loserBg = useColorModeValue('red.50', 'rgba(239, 68, 68, 0.1)');

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
            size="lg"
            fontFamily="heading"
            textTransform="uppercase"
            letterSpacing="wider"
          >
            Team 1
          </Heading>
          {team1Won && (
            <Badge
              colorScheme="green"
              fontSize="md"
              px={3}
              py={1}
              fontFamily="heading"
            >
              <Icon as={FiAward} mr={1} />
              VICTORY
            </Badge>
          )}
        </HStack>
        <Card
          bg={team1Won ? winnerBg : loserBg}
          border="2px solid"
          borderColor={team1Won ? 'shield.500' : 'red.500'}
        >
          <CardBody>
            <TableContainer>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th fontFamily="heading">OPERATIVE</Th>
                    <Th fontFamily="heading">RACE</Th>
                    <Th isNumeric fontFamily="heading">
                      MMR BEFORE
                    </Th>
                    <Th isNumeric fontFamily="heading">
                      MMR AFTER
                    </Th>
                    <Th isNumeric fontFamily="heading">
                      CHANGE
                    </Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {team1Players.map((player, idx) => (
                    <Tr key={idx}>
                      <Td fontWeight="bold" fontFamily="heading">
                        {player.player_name}
                      </Td>
                      <Td>
                        <Badge fontFamily="heading">{player.race}</Badge>
                      </Td>
                      <Td isNumeric>{Math.round(player.mmr_before)}</Td>
                      <Td isNumeric>{Math.round(player.mmr_after)}</Td>
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
          </CardBody>
        </Card>
      </Box>

      {/* Team 2 */}
      <Box>
        <HStack mb={4} spacing={3}>
          <Heading
            size="lg"
            fontFamily="heading"
            textTransform="uppercase"
            letterSpacing="wider"
          >
            Team 2
          </Heading>
          {!team1Won && (
            <Badge
              colorScheme="green"
              fontSize="md"
              px={3}
              py={1}
              fontFamily="heading"
            >
              <Icon as={FiAward} mr={1} />
              VICTORY
            </Badge>
          )}
        </HStack>
        <Card
          bg={team1Won ? loserBg : winnerBg}
          border="2px solid"
          borderColor={team1Won ? 'red.500' : 'shield.500'}
        >
          <CardBody>
            <TableContainer>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th fontFamily="heading">OPERATIVE</Th>
                    <Th fontFamily="heading">RACE</Th>
                    <Th isNumeric fontFamily="heading">
                      MMR BEFORE
                    </Th>
                    <Th isNumeric fontFamily="heading">
                      MMR AFTER
                    </Th>
                    <Th isNumeric fontFamily="heading">
                      CHANGE
                    </Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {team2Players.map((player, idx) => (
                    <Tr key={idx}>
                      <Td fontWeight="bold" fontFamily="heading">
                        {player.player_name}
                      </Td>
                      <Td>
                        <Badge fontFamily="heading">{player.race}</Badge>
                      </Td>
                      <Td isNumeric>{Math.round(player.mmr_before)}</Td>
                      <Td isNumeric>{Math.round(player.mmr_after)}</Td>
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
          </CardBody>
        </Card>
      </Box>
    </VStack>
  );
};

export default OperativesTab;
