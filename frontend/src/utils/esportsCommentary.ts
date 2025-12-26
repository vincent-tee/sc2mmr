/**
 * Esports Commentary Generator
 *
 * Generates unique, varied esports-style commentary for match statistics.
 * Designed to stay fresh across 100s of games with randomized phrases.
 */

// Seeded random for consistent commentary per match
const seededRandom = (seed: number) => {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
};

// Hash string to number for seeding
const hashString = (str: string): number => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
};

// Pick random item from array using seed
const pickRandom = <T>(arr: T[], seed: number): T => {
  const index = Math.floor(seededRandom(seed) * arr.length);
  return arr[index];
};

// ============================================================================
// DAMAGE COMMENTARY
// ============================================================================

const DAMAGE_INTROS = [
  '💥 DEVASTATING!',
  '🔥 EXPLOSIVE!',
  '⚡ ELECTRIFYING!',
  '💀 BRUTAL!',
  '🎯 SURGICAL!',
  '⚔️ RELENTLESS!',
  '🌋 ERUPTION!',
  '🚀 OBLITERATION!',
  '💣 CARNAGE!',
  '⭐ DOMINANT!',
];

const DAMAGE_VERBS = [
  'unleashed',
  'delivered',
  'dealt',
  'inflicted',
  'dropped',
  'pumped out',
  'landed',
  'smashed through',
  'racked up',
  'dished out',
  'brought down',
  'hammered',
  'crushed with',
  'obliterated with',
  'devastated with',
];

const DAMAGE_OBJECTS = [
  'of pure destruction',
  'of raw damage',
  'of punishment',
  'of annihilation',
  'of devastation',
  'worth of pain',
  'in combat value',
  'of army obliteration',
  'of battlefield dominance',
  'of explosive power',
];

const DAMAGE_HIGH_RATIO_PHRASES = [
  'Trading like a BOSS! 🏆',
  'Flawless army control!',
  'Absolutely SURGICAL efficiency!',
  "That's how you trade armies!",
  'Economy of motion, maximum destruction!',
  'TEXTBOOK army management!',
  'Clean, clinical, DEVASTATING!',
  'The efficiency is OFF THE CHARTS!',
  'Making every unit COUNT!',
  'MASTERCLASS in unit preservation!',
  'Trading at INSANE efficiency!',
  'This is what peak performance looks like!',
  "They're playing chess while others play checkers!",
  'CALCULATED destruction!',
  'Reading the game PERFECTLY!',
];

const DAMAGE_MEDIUM_RATIO_PHRASES = [
  'Solid trading throughout!',
  'Consistent pressure all game!',
  'Reliable damage output!',
  'Strong combat presence!',
  'Keeping up the pressure!',
  'Steady hands, steady wins!',
  'Maintained the momentum!',
  'Holding their own in every fight!',
  'Combat fundamentals on point!',
  'Getting value from every engagement!',
];

const DAMAGE_LOW_RATIO_PHRASES = [
  'Fighting through adversity!',
  'Taking hits but staying in it!',
  'Absorbing pressure for the team!',
  'The sacrificial warrior!',
  'Drawing fire like a champ!',
  'Taking one for the team!',
  'Frontline fighter mentality!',
  'Soaking damage, creating space!',
  'The tank of the squad!',
  'Brave, bold, battle-hardened!',
];

export const generateDamageCommentary = (
  playerName: string,
  damageDealt: number,
  damageRatio: number,
  matchId: number
): string => {
  const seed = hashString(`${playerName}-damage-${matchId}`);

  const intro = pickRandom(DAMAGE_INTROS, seed);
  const verb = pickRandom(DAMAGE_VERBS, seed + 1);
  const object = pickRandom(DAMAGE_OBJECTS, seed + 2);

  let ratioComment: string;
  if (damageRatio >= 2.0) {
    ratioComment = pickRandom(DAMAGE_HIGH_RATIO_PHRASES, seed + 3);
  } else if (damageRatio >= 1.0) {
    ratioComment = pickRandom(DAMAGE_MEDIUM_RATIO_PHRASES, seed + 3);
  } else {
    ratioComment = pickRandom(DAMAGE_LOW_RATIO_PHRASES, seed + 3);
  }

  const damageFormatted = damageDealt.toLocaleString();
  const ratioFormatted = damageRatio >= 100 ? '∞' : damageRatio.toFixed(1);

  return `${intro} ${playerName} ${verb} ${damageFormatted} ${object}! ${ratioFormatted}:1 ratio. ${ratioComment}`;
};

// ============================================================================
// WIN/LOSS COMMENTARY
// ============================================================================

const WIN_OPENERS = [
  '🏆 VICTORY!',
  '👑 CHAMPIONS!',
  '🎉 WINNERS!',
  '✨ TRIUMPHANT!',
  '🥇 CONQUERED!',
  '🔥 DOMINANT!',
  '⚡ ELECTRIC WIN!',
  '💪 CRUSHING IT!',
  '🌟 STELLAR!',
  '🚀 UNSTOPPABLE!',
];

const WIN_PHRASES = [
  'secured the W with AUTHORITY!',
  'proved why they\'re the best!',
  'showed CHAMPIONSHIP form!',
  'came out SWINGING and won!',
  'delivered when it MATTERED!',
  'clinched victory in STYLE!',
  'made it look EASY!',
  'owned that battlefield!',
  'put on a CLINIC!',
  'dominated from start to finish!',
  'wrote the playbook on winning!',
  'brought their A-GAME!',
  'sealed the deal DECISIVELY!',
  'claimed victory CONVINCINGLY!',
  'left no doubt about the outcome!',
];

const LOSS_OPENERS = [
  '💔 DEFEAT...',
  '😤 SO CLOSE!',
  '🥊 BATTLED HARD!',
  '⚔️ FOUGHT VALIANTLY!',
  '🎯 ALMOST HAD IT!',
];

const LOSS_PHRASES = [
  'fought hard but came up short.',
  'gave it their all - respect!',
  'showed heart despite the loss.',
  'will come back stronger!',
  'never gave up till the end.',
  'kept fighting to the last.',
  'learned valuable lessons today.',
  'took some lumps but still standing.',
  "weren't giving anything away easy!",
  'made them work for every inch!',
];

export const generateWinLossCommentary = (
  won: boolean,
  teamName: string,
  matchId: number
): string => {
  const seed = hashString(`${teamName}-result-${matchId}`);

  if (won) {
    const opener = pickRandom(WIN_OPENERS, seed);
    const phrase = pickRandom(WIN_PHRASES, seed + 1);
    return `${opener} ${teamName} ${phrase}`;
  } else {
    const opener = pickRandom(LOSS_OPENERS, seed);
    const phrase = pickRandom(LOSS_PHRASES, seed + 1);
    return `${opener} ${teamName} ${phrase}`;
  }
};

// ============================================================================
// ECONOMY COMMENTARY
// ============================================================================

const ECONOMY_HIGH_PHRASES = [
  '💰 BANK rolling! Economic POWERHOUSE!',
  '📈 Money printer going BRRR!',
  '🏦 The economy is BOOMING!',
  '💎 Mining like there\'s no tomorrow!',
  '🤑 Economic MASTERMIND at work!',
  '💵 Showing how to MACRO like a pro!',
  '🏭 Production facilities MAXED OUT!',
  '⛏️ Resource collection ELITE tier!',
  '💲 Making BANK every second!',
  '🌟 Economic fundamentals ON POINT!',
];

const ECONOMY_MEDIUM_PHRASES = [
  '💰 Solid economic foundation!',
  '📊 Steady resource flow!',
  '🔧 Keeping the economy ticking!',
  '⚙️ Production humming along nicely!',
  '💵 Smart resource management!',
];

const ECONOMY_LOW_PHRASES = [
  '⚔️ Prioritized aggression over economy!',
  '🎯 All-in mentality!',
  '💥 Fighting over farming!',
  '🔥 Aggro style, low macro!',
  '⚡ Speed over greed!',
];

export const generateEconomyCommentary = (
  resourcesCollected: number,
  avgResources: number,
  matchId: number,
  playerName: string
): string => {
  const seed = hashString(`${playerName}-econ-${matchId}`);
  const ratio = resourcesCollected / Math.max(avgResources, 1);

  let phrase: string;
  if (ratio >= 1.3) {
    phrase = pickRandom(ECONOMY_HIGH_PHRASES, seed);
  } else if (ratio >= 0.8) {
    phrase = pickRandom(ECONOMY_MEDIUM_PHRASES, seed);
  } else {
    phrase = pickRandom(ECONOMY_LOW_PHRASES, seed);
  }

  return `${phrase} ${resourcesCollected.toLocaleString()} resources harvested!`;
};

// ============================================================================
// MVP COMMENTARY
// ============================================================================

const MVP_INTROS = [
  '🌟 MVP ALERT!',
  '👑 THE CARRY!',
  '🏆 STAR PLAYER!',
  '⭐ SPOTLIGHT ON:',
  '🔥 MATCH HERO:',
  '💎 DIAMOND PERFORMANCE!',
  '🚀 GAME CHANGER:',
  '⚡ ELECTRIC PLAYER:',
  '🎯 CLUTCH PERFORMER:',
  '💪 THE DIFFERENCE MAKER:',
];

const MVP_DESCRIPTIONS = [
  'absolutely DOMINATED this match!',
  'carried the team to victory!',
  'put on a MASTERCLASS performance!',
  'was UNSTOPPABLE today!',
  'showed why they\'re a BEAST!',
  'made ALL the right plays!',
  'was the X-FACTOR for their team!',
  'elevated the entire squad!',
  'delivered a LEGENDARY performance!',
  'was HEAD AND SHOULDERS above!',
  'played out of their MIND!',
  'brought the HEAT when it mattered!',
  'showed up BIG TIME!',
  'was the MVP without question!',
  'left everyone in AWE!',
];

export const generateMVPCommentary = (
  playerName: string,
  impactScore: number,
  matchId: number
): string => {
  const seed = hashString(`${playerName}-mvp-${matchId}`);

  const intro = pickRandom(MVP_INTROS, seed);
  const desc = pickRandom(MVP_DESCRIPTIONS, seed + 1);

  return `${intro} ${playerName} ${desc} Impact: ${impactScore.toFixed(0)}/100`;
};

// ============================================================================
// MATCH OVERVIEW COMMENTARY
// ============================================================================

const QUICK_MATCH_PHRASES = [
  '⚡ LIGHTNING FAST! This one was over before it started!',
  '🚀 SPEEDRUN! A decisive early victory!',
  '💨 BLITZ! They came, they saw, they conquered!',
  '⏱️ QUICK WORK! Efficiency at its finest!',
  '🎯 SURGICAL STRIKE! Clean and fast!',
];

const LONG_MATCH_PHRASES = [
  '⚔️ EPIC BATTLE! An absolute war of attrition!',
  '🏰 SIEGE WARFARE! Both teams dug in deep!',
  '💪 MARATHON! A true test of endurance!',
  '🔥 GRUELING! Every advantage was fought for!',
  '⭐ LEGENDARY! One for the history books!',
];

const NORMAL_MATCH_PHRASES = [
  '🎮 SOLID MATCH! Good plays on both sides!',
  '⚔️ COMPETITIVE! Teams went back and forth!',
  '🎯 WELL PLAYED! Clean execution throughout!',
  '💥 ACTION-PACKED! Plenty of excitement!',
  '🔥 ENGAGING! A game worth watching!',
];

export const generateMatchOverview = (
  durationSeconds: number,
  mapName: string,
  gameMode: string,
  matchId: number
): string => {
  const seed = hashString(`overview-${matchId}`);

  let phrase: string;
  if (durationSeconds < 300) {
    phrase = pickRandom(QUICK_MATCH_PHRASES, seed);
  } else if (durationSeconds > 1200) {
    phrase = pickRandom(LONG_MATCH_PHRASES, seed);
  } else {
    phrase = pickRandom(NORMAL_MATCH_PHRASES, seed);
  }

  const mins = Math.floor(durationSeconds / 60);
  const secs = durationSeconds % 60;

  return `${phrase} ${gameMode} on ${mapName} • ${mins}:${secs.toString().padStart(2, '0')}`;
};

// ============================================================================
// UPSET COMMENTARY
// ============================================================================

const UPSET_PHRASES = [
  '🤯 UPSET ALERT! The underdogs did it!',
  '😱 WHAT A SHOCKER! Nobody saw this coming!',
  '🔥 AGAINST ALL ODDS! Incredible upset!',
  '💪 NEVER COUNT THEM OUT! Massive upset!',
  '⚡ CINDERELLA STORY! They pulled it off!',
  '🎯 CLUTCH FACTOR! When it mattered most!',
  '👑 GIANT SLAYERS! They took down the favorites!',
  '🚀 BRACKET BUSTERS! Predictions in shambles!',
  '💎 BELIEF WINS! They wanted it more!',
  '⭐ MAGIC HAPPENS! The underdog prevails!',
];

export const generateUpsetCommentary = (
  winProbability: number,
  matchId: number
): string | null => {
  if (winProbability >= 0.4) return null; // Not an upset

  const seed = hashString(`upset-${matchId}`);
  const phrase = pickRandom(UPSET_PHRASES, seed);
  const prob = (winProbability * 100).toFixed(0);

  return `${phrase} Only ${prob}% chance to win!`;
};

// ============================================================================
// PLAYER HIGHLIGHT ONE-LINERS
// ============================================================================

interface PlayerStats {
  name: string;
  won: boolean;
  damageDealt: number;
  damageRatio: number;
  impactScore?: number;
  resourcesCollected?: number;
  unitsKilled?: number;
}

export const generatePlayerHighlight = (
  stats: PlayerStats,
  matchId: number
): string => {
  const seed = hashString(`${stats.name}-highlight-${matchId}`);

  // Determine the most impressive stat
  const highlights: string[] = [];

  if (stats.damageDealt > 20000) {
    highlights.push(generateDamageCommentary(stats.name, stats.damageDealt, stats.damageRatio, matchId));
  }

  if (stats.impactScore && stats.impactScore >= 70) {
    highlights.push(generateMVPCommentary(stats.name, stats.impactScore, matchId));
  }

  if (highlights.length === 0) {
    // Fallback generic highlight
    const GENERIC_HIGHLIGHTS = [
      `⚔️ ${stats.name} brought the heat this match!`,
      `🎮 ${stats.name} showed up and showed out!`,
      `💪 ${stats.name} put in WORK today!`,
      `🔥 ${stats.name} was in the mix all game!`,
      `⚡ ${stats.name} made their presence felt!`,
      `🎯 ${stats.name} contributed to the cause!`,
      `💥 ${stats.name} was active on the battlefield!`,
      `⭐ ${stats.name} played their role well!`,
    ];
    return pickRandom(GENERIC_HIGHLIGHTS, seed);
  }

  return pickRandom(highlights, seed);
};

// ============================================================================
// TEAM SUMMARY GENERATOR
// ============================================================================

export const generateTeamSummary = (
  teamNumber: number,
  won: boolean,
  avgImpact: number,
  totalDamage: number,
  matchId: number
): string => {
  const seed = hashString(`team${teamNumber}-${matchId}`);

  const teamLabel = `Team ${teamNumber}`;
  const resultComment = generateWinLossCommentary(won, teamLabel, matchId);

  let performanceComment: string;
  if (avgImpact >= 70) {
    const HIGH_TEAM_PHRASES = [
      'Elite-level team performance!',
      'Coordinated like a championship squad!',
      'Teamwork makes the dream work!',
      'Playing like a well-oiled machine!',
      'Peak team synergy achieved!',
    ];
    performanceComment = pickRandom(HIGH_TEAM_PHRASES, seed + 10);
  } else if (avgImpact >= 50) {
    const MED_TEAM_PHRASES = [
      'Solid team effort all around!',
      'Everyone pulled their weight!',
      'Consistent contribution from all!',
      'Good team chemistry on display!',
      'Balanced team performance!',
    ];
    performanceComment = pickRandom(MED_TEAM_PHRASES, seed + 10);
  } else {
    const LOW_TEAM_PHRASES = [
      'Room for improvement, but they tried!',
      'Learning experience for the squad!',
      'Building for next time!',
      'Taking notes for the rematch!',
      'Every game makes you stronger!',
    ];
    performanceComment = pickRandom(LOW_TEAM_PHRASES, seed + 10);
  }

  return `${resultComment} ${performanceComment} Combined damage: ${totalDamage.toLocaleString()}`;
};
