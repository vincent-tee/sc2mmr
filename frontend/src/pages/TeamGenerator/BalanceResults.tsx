/**
 * BalanceResults Component - Team Balance Suggestions Display
 * Shows balance results and allows export of team configurations
 * Includes celebration animations for well-balanced teams
 */
import { useRef, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Heading,
  VStack,
  HStack,
  Text,
  Badge,
  Icon,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Button,
  Tooltip,
  IconButton,
  useToast,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { toJpeg, toBlob } from 'html-to-image';
import {
  FiCopy,
  FiDownload,
  FiShare2,
  FiCheck,
  FiStar,
  FiImage,
  FiChevronUp,
  FiClipboard,
  FiUpload,
  FiSliders,
} from 'react-icons/fi';
import TacticalCard from '@/components/TacticalCard';
import VSScreen from '@/components/VSScreen';
import { formatMMR } from '@/utils/formatting';
import type { TeamSuggestionWithImpact } from '@/types/api';
import { FiAlertTriangle } from 'react-icons/fi';

const TacticalForecastOverlay: React.FC<{ forecast: any }> = ({ forecast }) => {
  if (!forecast || (!forecast.map_specialists?.length && !forecast.playstyle_alerts?.length)) return null;

  return (
    <VStack align="stretch" spacing={2} mb={4} w="100%">
      {forecast.map_specialists.map((s: any, i: number) => (
        <Alert key={i} status="info" variant="solid" bg="brand.600" borderRadius="md" py={1}>
          <AlertIcon as={FiStar} />
          <Box flex="1">
            <Text fontSize="xs" fontWeight="bold">
              MAP EXPERT: {s.player_name} ({s.win_rate}% WR)
            </Text>
          </Box>
        </Alert>
      ))}
      {forecast.playstyle_alerts.map((a: any, i: number) => (
        <Alert key={i} status="warning" variant="solid" bg="orange.600" borderRadius="md" py={1}>
          <AlertIcon as={FiAlertTriangle} />
          <Box flex="1">
            <Text fontSize="xs" fontWeight="bold">
              TACTICAL RISK: {a.player_name} - {a.alert} ({a.confidence}% profile)
            </Text>
          </Box>
        </Alert>
      ))}
    </VStack>
  );
};


// Celebration animation keyframes
const celebrationPulse = keyframes`
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.9; }
  100% { transform: scale(1); opacity: 1; }
`;

const confettiFloat = keyframes`
  0% { transform: translateY(0) rotate(0deg); opacity: 1; }
  100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
`;

const starBurst = keyframes`
  0% { transform: scale(0) rotate(0deg); opacity: 0; }
  50% { transform: scale(1.2) rotate(180deg); opacity: 1; }
  100% { transform: scale(1) rotate(360deg); opacity: 1; }
`;

const slideInBounce = keyframes`
  0% { transform: translateY(20px); opacity: 0; }
  60% { transform: translateY(-5px); opacity: 1; }
  100% { transform: translateY(0); opacity: 1; }
`;

// Celebration banner component
const CelebrationBanner: React.FC<{ fairnessRating: string }> = ({ fairnessRating }) => {
  const [show, setShow] = useState(true);
  
  useEffect(() => {
    const timer = setTimeout(() => setShow(false), 4000);
    return () => clearTimeout(timer);
  }, []);
  
  if (!show) return null;
  
  const isPerfect = fairnessRating === 'Perfect';
  
  return (
    <Box
      position="fixed"
      top="50%"
      left="50%"
      transform="translate(-50%, -50%)"
      zIndex={1000}
      animation={`${celebrationPulse} 0.5s ease-in-out`}
      pointerEvents="none"
    >
      <Box
        bg={isPerfect ? 'shield.500' : 'brand.500'}
        color={isPerfect ? 'space.900' : 'white'}
        px={10}
        py={6}
        borderRadius="2xl"
        border="4px solid"
        borderColor="space.900"
        boxShadow="8px 8px 0 var(--chakra-colors-space-900)"
        textAlign="center"
      >
        <HStack justify="center" spacing={4} mb={2}>
          <Icon 
            as={isPerfect ? FiStar : FiCheck} 
            boxSize={10} 
            animation={`${starBurst} 0.6s ease-out`}
          />
          <Heading size="xl" fontFamily="heading" fontWeight="black">
            {isPerfect ? 'Perfect Balance!' : 'Teams Balanced!'}
          </Heading>
          <Icon 
            as={isPerfect ? FiStar : FiCheck} 
            boxSize={10} 
            animation={`${starBurst} 0.6s ease-out 0.1s`}
          />
        </HStack>
        <Text fontSize="lg" fontWeight="bold" opacity={0.9}>
          {isPerfect 
            ? 'These teams are perfectly matched!' 
            : 'Great team configuration found!'}
        </Text>
      </Box>
      
      {isPerfect && (
        <>
          {[...Array(12)].map((_, i) => (
            <Box
              key={i}
              position="absolute"
              top="100%"
              left={`${10 + i * 7}%`}
              width="10px"
              height="10px"
              borderRadius="full"
              bg={['gold', 'green.400', 'blue.400', 'purple.400', 'orange.400'][i % 5]}
              animation={`${confettiFloat} ${1 + Math.random()}s ease-out forwards`}
              style={{ animationDelay: `${i * 0.1}s` }}
            />
          ))}
        </>
      )}
    </Box>
  );
};

interface BalanceResultsProps {
  suggestions: TeamSuggestionWithImpact[];
  onExport: (
    suggestion: TeamSuggestionWithImpact,
    format: 'text' | 'download'
  ) => Promise<void>;
  onExportAll: () => Promise<void>;
  onClear: () => void;
}

const BalanceResults: React.FC<BalanceResultsProps> = ({
  suggestions,
  onExport,
  onExportAll,
  onClear,
}) => {
  const navigate = useNavigate();
  const [showCelebration, setShowCelebration] = useState(false);
  const [celebrationRating, setCelebrationRating] = useState<string>('');
  const [selectedConfigIndex, setSelectedConfigIndex] = useState(0);

  useEffect(() => {
    if (suggestions.length > 0) {
      setSelectedConfigIndex(0);
      const topRating = suggestions[0].fairness_rating;
      if (topRating === 'Perfect' || topRating === 'Very Good') {
        setCelebrationRating(topRating);
        setShowCelebration(true);
        const timer = setTimeout(() => setShowCelebration(false), 4500);
        return () => clearTimeout(timer);
      }
    }
  }, [suggestions]);

  if (suggestions.length === 0) {
    return null;
  }

  return (
    <Box>
      {showCelebration && <CelebrationBanner fairnessRating={celebrationRating} />}
      
      <HStack justify="center" mb={6} spacing={4}>
        <Button
          size="sm"
          variant="ghost"
          colorScheme="gray"
          leftIcon={<FiChevronUp />}
          onClick={onClear}
          fontFamily="heading"
        >
          BACK TO SQUAD
        </Button>
        <Heading
          size="lg"
          fontFamily="heading"
          letterSpacing="wider"
          color="brand.400"
          animation={suggestions.length > 0 ? `${slideInBounce} 0.5s ease-out` : undefined}
          id="balance-results"
        >
          Team Configurations
        </Heading>
        {suggestions.length >= 2 && (
          <Button
            size="sm"
            colorScheme="brand"
            variant="outline"
            leftIcon={<FiCopy />}
            onClick={onExportAll}
            fontFamily="heading"
          >
            Copy Teams
          </Button>
        )}
        <Button
          size="sm"
          colorScheme="brand"
          leftIcon={<FiUpload />}
          onClick={() => navigate('/upload')}
          fontFamily="heading"
        >
          Play It, Then Upload Replay
        </Button>
      </HStack>

      <Box bg="space.800" p={2} borderRadius="xl" border="2px solid" borderColor="space.700" mb={6}>
        <HStack spacing={2} overflowX="auto" pb={2}>
          {suggestions.map((_, index) => {
            const labels = ['OPTIMAL', 'TACTICAL', 'ALT 1', 'ALT 2'];
            return (
              <Button
                key={index}
                flex={1}
                size="md"
                variant={selectedConfigIndex === index ? 'solid' : 'ghost'}
                colorScheme={selectedConfigIndex === index ? 'brand' : 'gray'}
                onClick={() => setSelectedConfigIndex(index)}
                fontFamily="heading"
                fontSize="xs"
                letterSpacing="widest"
              >
                {labels[index] || `CONFIG ${index + 1}`}
              </Button>
            );
          })}
          <Tooltip label="Match Quality: TrueSkill draw probability. All configs have similar quality since they use the same players." hasArrow placement="top">
            <Badge
              colorScheme="purple"
              variant="subtle"
              fontSize="xs"
              px={3}
              py={1}
              borderRadius="md"
              cursor="help"
              borderBottomWidth="1px"
              borderBottomStyle="dotted"
              borderColor="whiteAlpha.500"
            >
              Quality: {suggestions[0].match_quality.toFixed(0)}%
            </Badge>
          </Tooltip>
        </HStack>
      </Box>

      <Box
        animation={`${slideInBounce} 0.5s ease-out`}
        key={selectedConfigIndex}
      >
        <TeamSuggestionCard
          suggestion={suggestions[selectedConfigIndex]}
          index={selectedConfigIndex}
          isRecommended={selectedConfigIndex === 0}
          onExport={onExport}
        />
      </Box>
    </Box>
  );
};

interface TeamSuggestionCardProps {
  suggestion: TeamSuggestionWithImpact;
  index: number;
  isRecommended: boolean;
  onExport: (
    suggestion: TeamSuggestionWithImpact,
    format: 'text' | 'download'
  ) => Promise<void>;
}

const getSuggestionDescription = (index: number): string => {
  switch (index) {
    case 0:
      return 'Optimal Balance: The mathematically superior split with the smallest possible skill gap between teams.';
    case 1:
      return 'Tactical Synergy: Prioritizes player chemistry. Groups players who historically win more often when on the same side.';
    default:
      return 'Alternative Config: A competitive alternative configuration with high match quality.';
  }
};

const TeamSuggestionCard: React.FC<TeamSuggestionCardProps> = ({
  suggestion,
  index,
  isRecommended,
  onExport,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const toast = useToast();
  const navigate = useNavigate();

  const handleFineTune = (): void => {
    navigate('/predictor', {
      state: {
        initialTeam1Ids: suggestion.team_1.players.map((p) => p.id),
        initialTeam2Ids: suggestion.team_2.players.map((p) => p.id),
      },
    });
  };

  const handleImageExport = async () => {
    if (cardRef.current === null) return;
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    try {
      const dataUrl = await toJpeg(cardRef.current, { 
        quality: 0.95,
        backgroundColor: '#0a0f1c'
      });
      
      const link = document.createElement('a');
      link.download = `sc2-match-config-${index + 1}.jpg`;
      link.href = dataUrl;
      link.click();
      
      toast({
        title: 'Tactical Briefing Exported',
        description: 'Match configuration saved as JPEG',
        status: 'success',
        duration: 2000,
      });
    } catch (err) {
      console.error('Failed to export image', err);
      toast({
        title: 'Export Failed',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const handleCopyImage = async () => {
    if (cardRef.current === null) return;

    await new Promise(resolve => setTimeout(resolve, 100));

    try {
      const blob = await toBlob(cardRef.current, {
        backgroundColor: '#0a0f1c'
      });
      
      if (!blob) throw new Error('Failed to create blob');

      const item = new ClipboardItem({ 'image/png': blob });
      await navigator.clipboard.write([item]);

      toast({
        title: 'Image Copied!',
        description: 'Match configuration copied to clipboard',
        status: 'success',
        duration: 2000,
      });
    } catch (err) {
      console.error('Failed to copy image', err);
      toast({
        title: 'Copy Failed',
        description: 'Your browser may not support copying images.',
        status: 'error',
        duration: 3000,
      });
    }
  };

  const labels = ['Optimal Balance', 'Tactical Synergy', 'Alternative Config'];


  const label = labels[index] || `Config ${index + 1}`;
  const description = getSuggestionDescription(index);

  const activeColor = isRecommended ? 'shield.400' : 'brand.400';
  const glowIntensity = isRecommended ? '20px' : '10px';

  const synergy_score = suggestion.total_synergy || 0;

  const vsScreenData = {
    team1: {
      players: suggestion.team_1.players.map(p => ({
        name: p.name,
        mmr: Math.round(p.mmr),
        race: p.favorite_race || 'Random',
      })),
      // Sum player display MMRs directly; the API's avg_mmr is still unified-based
      totalMMR: Math.round(suggestion.team_1.players.reduce((sum, p) => sum + p.mmr, 0)),
      winProbability: suggestion.win_probability_team_1,
      synergyBonus: synergy_score > 0 ? synergy_score : undefined,
    },
    team2: {
      players: suggestion.team_2.players.map(p => ({
        name: p.name,
        mmr: Math.round(p.mmr),
        race: p.favorite_race || 'Random',
      })),
      totalMMR: Math.round(suggestion.team_2.players.reduce((sum, p) => sum + p.mmr, 0)),
      winProbability: suggestion.win_probability_team_2,
      synergyBonus: synergy_score < 0 ? Math.abs(synergy_score) : undefined,
    },
    matchInfo: {
      mapName: `${suggestion.team_1.players.length}v${suggestion.team_2.players.length} Match`,
      gameMode: suggestion.fairness_rating + ' Balance',
    },
  };


  return (
    <Box position="relative" ref={cardRef}>
      <Box
        position="absolute"
        top="-10px"
        left="-10px"
        fontSize="6xl"
        opacity="0.05"
        fontWeight="black"
        pointerEvents="none"
        userSelect="none"
        fontFamily="heading"
        color={activeColor}
      >
        0{index + 1}
      </Box>

      <TacticalCard
        variant={isRecommended ? 'command' : index % 2 === 0 ? 'angled' : 'default'}
        glowColor={
          isRecommended
            ? 'rgba(0, 255, 136, 0.6)'
            : 'rgba(0, 212, 255, 0.4)'
        }
      >
        <Box p={5} position="relative" overflow="hidden">
          <HStack justify="space-between" mb={3}>
            <VStack align="start" spacing={0}>
              <HStack spacing={3}>
                <Box 
                  w="4px" 
                  h="24px" 
                  bg={activeColor} 
                  boxShadow={`0 0 ${glowIntensity} var(--chakra-colors-${activeColor.split('.')[0]}-500)`}
                />
                <Heading
                  size="md"
                  fontFamily="heading"
                  letterSpacing="widest"
                  color="gray.100"
                  textTransform="uppercase"
                >
                  {label}
                </Heading>
              </HStack>
              <Text fontSize="2xs" color="gray.500" mt={1} maxW="400px" noOfLines={1}>
                {description}
              </Text>
            </VStack>
            
            <HStack spacing={2}>
              <Tooltip label="MMR Gap: The difference in total skill points between teams." hasArrow placement="top">
                <Badge
                  colorScheme="blue"
                  variant="subtle"
                  fontSize="2xs"
                  px={2}
                  borderRadius="sm"
                  cursor="help"
                  borderBottomWidth="1px"
                  borderBottomStyle="dotted"
                  borderColor="whiteAlpha.500"
                >
                  GAP: {formatMMR(suggestion.mmr_difference)}
                </Badge>
              </Tooltip>
              {suggestion.impact_balance_score && (
                <Tooltip label="Team Fit: How evenly high-impact players are distributed across both teams." hasArrow placement="top">
                  <Badge
                    colorScheme="green"
                    variant="subtle"
                    fontSize="2xs"
                    px={2}
                    borderRadius="sm"
                    cursor="help"
                    borderBottomWidth="1px"
                    borderBottomStyle="dotted"
                    borderColor="whiteAlpha.500"
                  >
                    FIT: {suggestion.impact_balance_score.toFixed(0)}%
                  </Badge>
                </Tooltip>
              )}
              <Button
                size="xs"
                variant="outline"
                colorScheme="brand"
                leftIcon={<FiSliders />}
                onClick={handleFineTune}
                fontFamily="heading"
              >
                Fine-tune this split
              </Button>
              <Menu>
                <MenuButton
                  as={IconButton}
                  icon={<FiShare2 />}
                  size="xs"
                  variant="solid"
                  colorScheme="brand"
                  aria-label="Export options"
                />
                <MenuList bg="gray.800" borderColor="brand.500" zIndex={20}>
                  <MenuItem icon={<FiClipboard />} onClick={handleCopyImage} fontSize="xs">Copy as Image</MenuItem>
                  <MenuItem icon={<FiImage />} onClick={handleImageExport} fontSize="xs">Save as Image</MenuItem>
                  <MenuItem icon={<FiCopy />} onClick={() => onExport(suggestion, 'text')} fontSize="xs">Copy Text</MenuItem>
                  <MenuItem icon={<FiDownload />} onClick={() => onExport(suggestion, 'download')} fontSize="xs">Download File</MenuItem>
                </MenuList>
              </Menu>
            </HStack>
          </HStack>

          <Box 
            p={1} 
            bg="rgba(0,0,0,0.2)" 
            borderRadius="lg" 
            border="1px solid" 
            borderColor="whiteAlpha.100"
            position="relative"
          >
            {suggestion.tactical_forecast && (
              <TacticalForecastOverlay forecast={suggestion.tactical_forecast} />
            )}
        <VSScreen
          team1={vsScreenData.team1}
          team2={vsScreenData.team2}
          matchInfo={vsScreenData.matchInfo}
          winner={suggestion.win_probability_team_1 > 50 ? 1 : suggestion.win_probability_team_2 > 50 ? 2 : null}
          isPrediction={true}
        />
          </Box>
        </Box>
      </TacticalCard>
    </Box>
  );
};

export default BalanceResults;
