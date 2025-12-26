/**
 * Centralized Animation Definitions
 *
 * Provides reusable keyframe animations for the SC2 MMR Tracker application.
 * Extracted from component-level definitions to enable DRY principle and
 * consistent animation usage across the entire application.
 *
 * Theme: StarCraft-inspired tactical UI with tactical blues, vespene golds,
 * and protoss greens creating a sci-fi aesthetic.
 */

/**
 * Pulse Glow Animation
 *
 * Used for: Background glows behind avatars, stat indicators
 * Purpose: Creates a subtle breathing effect to draw attention
 *
 * Examples:
 * - HexagonalStat background glow (opacity 0.1 → 0.2, scale 1 → 1.05)
 * - PlayerCard avatar glow (opacity 0.2 → 0.4)
 */
export const pulseKeyframes = {
  '0%, 100%': {
    opacity: 0.1,
    transform: 'translate(-50%, -50%) scale(1)',
  },
  '50%': {
    opacity: 0.2,
    transform: 'translate(-50%, -50%) scale(1.05)',
  },
};

/**
 * Scanline Animation
 *
 * Used for: Tactical card overlay effect
 * Purpose: Creates a tactical scanner effect moving downward,
 *          giving tactical readout appearance to cards
 *
 * Effect: Moves a line from top to bottom of the card to simulate
 *         a scanning beam typical of RTS tactical displays
 */
export const scanlineKeyframes = {
  '0%': {
    transform: 'translateY(0)',
  },
  '100%': {
    transform: 'translateY(400px)',
  },
};

/**
 * Shimmer Animation
 *
 * Used for: Action buttons (Generate Teams), interactive elements
 * Purpose: Creates a shimmering highlight effect to emphasize
 *          important interactive elements
 *
 * Effect: Smooth opacity transition creating a glowing shimmer
 *         with a gold gradient background
 */
export const shimmerKeyframes = {
  '0%, 100%': {
    opacity: 0.5,
  },
  '50%': {
    opacity: 1,
  },
};

/**
 * Twinkle Animation
 *
 * Used for: Starfield background effect (body pseudo-element)
 * Purpose: Creates twinkling starfield in the background
 *
 * Effect: Subtle opacity variation to simulate distant stars
 *         twinkling in space
 */
export const twinkleKeyframes = {
  '0%, 100%': {
    opacity: 0.6,
  },
  '50%': {
    opacity: 1,
  },
};

/**
 * Fade In Animation
 *
 * Used for: Component mount animations, page transitions
 * Purpose: Smooth entrance animation for new elements
 *
 * Standard duration: 0.3s ease-out
 */
export const fadeInKeyframes = {
  from: {
    opacity: 0,
  },
  to: {
    opacity: 1,
  },
};

/**
 * Slide In Up Animation
 *
 * Used for: Card reveals, content animations
 * Purpose: Slides element up while fading in
 *
 * Standard duration: 0.3s ease-out
 */
export const slideInUpKeyframes = {
  from: {
    opacity: 0,
    transform: 'translateY(20px)',
  },
  to: {
    opacity: 1,
    transform: 'translateY(0)',
  },
};

/**
 * Slide In Left Animation
 *
 * Used for: Sidebar reveals, progressive layouts
 * Purpose: Slides element in from left side while fading in
 *
 * Standard duration: 0.3s ease-out
 */
export const slideInLeftKeyframes = {
  from: {
    opacity: 0,
    transform: 'translateX(-20px)',
  },
  to: {
    opacity: 1,
    transform: 'translateX(0)',
  },
};

/**
 * Tactical Glow Animation
 *
 * Used for: Hover effects on tactical elements, selected states
 * Purpose: Creates a glowing box-shadow effect with tactical blue
 *
 * Effect: Smooth color transition for tactical cyan glow
 */
export const tacticalGlowKeyframes = {
  '0%, 100%': {
    boxShadow: '0 0 5px rgba(0, 212, 255, 0.3)',
  },
  '50%': {
    boxShadow: '0 0 15px rgba(0, 212, 255, 0.6)',
  },
};

/**
 * Color Pulse Animation
 *
 * Used for: Status indicators, notifications
 * Purpose: Pulsing color effect to draw attention
 *
 * Can be used with different colors for various states
 */
export const colorPulseKeyframes = {
  '0%, 100%': {
    color: 'rgba(0, 212, 255, 0.6)',
  },
  '50%': {
    color: 'rgba(0, 212, 255, 1)',
  },
};

/**
 * Scale Bounce Animation
 *
 * Used for: Interactive feedback, button presses
 * Purpose: Bouncy scale effect for tactile feedback
 */
export const scaleBounceKeyframes = {
  '0%, 100%': {
    transform: 'scale(1)',
  },
  '50%': {
    transform: 'scale(1.05)',
  },
};

/**
 * Rotation Animation
 *
 * Used for: Loading spinners, rotatable elements
 * Purpose: Continuous 360-degree rotation
 */
export const rotationKeyframes = {
  from: {
    transform: 'rotate(0deg)',
  },
  to: {
    transform: 'rotate(360deg)',
  },
};

/**
 * Animation Utility Objects
 *
 * These objects combine keyframes with timing functions for
 * direct use in component styles. Use these for quick animation setup.
 */
export const animations = {
  /**
   * Pulse glow effect - 2s ease-in-out infinite
   * Used for subtle breathing effects on background glows
   */
  pulse: 'pulse 2s ease-in-out infinite',

  /**
   * Scanline effect - 3s linear infinite
   * Used for tactical scanning beam effects
   */
  scanline: 'scanline 3s linear infinite',

  /**
   * Shimmer effect - 2s ease-in-out infinite
   * Used for highlighting interactive elements
   */
  shimmer: 'shimmer 2s ease-in-out infinite',

  /**
   * Twinkle effect - 3s ease-in-out infinite
   * Used for starfield background
   */
  twinkle: 'twinkle 3s ease-in-out infinite',

  /**
   * Fade in effect - 0.3s ease-out (one-shot)
   * Used for initial element entrance
   */
  fadeIn: 'fadeIn 0.3s ease-out',

  /**
   * Slide up effect - 0.3s ease-out (one-shot)
   * Used for card and content reveals
   */
  slideInUp: 'slideInUp 0.3s ease-out',

  /**
   * Slide left effect - 0.3s ease-out (one-shot)
   * Used for sidebar and panel reveals
   */
  slideInLeft: 'slideInLeft 0.3s ease-out',

  /**
   * Tactical glow effect - 2s ease-in-out infinite
   * Used for tactical UI elements with pulsing glow
   */
  tacticalGlow: 'tacticalGlow 2s ease-in-out infinite',

  /**
   * Color pulse effect - 2s ease-in-out infinite
   * Used for status indicators and notifications
   */
  colorPulse: 'colorPulse 2s ease-in-out infinite',

  /**
   * Scale bounce effect - 0.6s ease-in-out infinite
   * Used for interactive feedback and button animations
   */
  scaleBounce: 'scaleBounce 0.6s ease-in-out infinite',

  /**
   * Rotation effect - 1s linear infinite
   * Used for loading spinners
   */
  rotation: 'rotation 1s linear infinite',
};

/**
 * Animation Configuration Map
 *
 * Provides descriptive information about each animation for
 * documentation, debugging, and dynamic usage.
 */
export const animationConfig = {
  pulse: {
    duration: '2s',
    timingFunction: 'ease-in-out',
    iterationCount: 'infinite',
    description: 'Subtle breathing pulse effect',
    useCase: ['avatar glow', 'background effects', 'stat indicators'],
  },
  scanline: {
    duration: '3s',
    timingFunction: 'linear',
    iterationCount: 'infinite',
    description: 'Tactical scanner beam effect',
    useCase: ['tactical cards', 'scanning effects'],
  },
  shimmer: {
    duration: '2s',
    timingFunction: 'ease-in-out',
    iterationCount: 'infinite',
    description: 'Shimmering highlight effect',
    useCase: ['action buttons', 'interactive elements', 'CTAs'],
  },
  twinkle: {
    duration: '3s',
    timingFunction: 'ease-in-out',
    iterationCount: 'infinite',
    description: 'Twinkling starfield effect',
    useCase: ['background', 'ambient effects'],
  },
  fadeIn: {
    duration: '0.3s',
    timingFunction: 'ease-out',
    iterationCount: '1',
    description: 'Fade in entrance animation',
    useCase: ['component mounting', 'page transitions', 'reveals'],
  },
  slideInUp: {
    duration: '0.3s',
    timingFunction: 'ease-out',
    iterationCount: '1',
    description: 'Slide up entrance animation',
    useCase: ['card reveals', 'content animations', 'modals'],
  },
  slideInLeft: {
    duration: '0.3s',
    timingFunction: 'ease-out',
    iterationCount: '1',
    description: 'Slide left entrance animation',
    useCase: ['sidebar reveals', 'side panels', 'progressive layouts'],
  },
  tacticalGlow: {
    duration: '2s',
    timingFunction: 'ease-in-out',
    iterationCount: 'infinite',
    description: 'Tactical cyan glow pulsing effect',
    useCase: ['hover states', 'selected states', 'tactical UI'],
  },
  colorPulse: {
    duration: '2s',
    timingFunction: 'ease-in-out',
    iterationCount: 'infinite',
    description: 'Color pulsing effect',
    useCase: ['status indicators', 'notifications', 'alerts'],
  },
  scaleBounce: {
    duration: '0.6s',
    timingFunction: 'ease-in-out',
    iterationCount: 'infinite',
    description: 'Bouncy scale effect',
    useCase: ['button feedback', 'interactive elements', 'attention'],
  },
  rotation: {
    duration: '1s',
    timingFunction: 'linear',
    iterationCount: 'infinite',
    description: '360-degree rotation',
    useCase: ['loading spinners', 'rotating elements'],
  },
};

/**
 * Animation Presets for Common Patterns
 *
 * Combines animations with their default configurations for
 * quick, semantic animation application.
 */
export const animationPresets = {
  /**
   * Entrance animations for components appearing on screen
   */
  entrance: {
    fade: animations.fadeIn,
    slideUp: animations.slideInUp,
    slideLeft: animations.slideInLeft,
  },

  /**
   * Attention-drawing animations for interactive elements
   */
  attention: {
    shimmer: animations.shimmer,
    pulse: animations.pulse,
    scaleBounce: animations.scaleBounce,
  },

  /**
   * Tactical/UI-specific animations for theme consistency
   */
  tactical: {
    scanline: animations.scanline,
    glow: animations.tacticalGlow,
    colorPulse: animations.colorPulse,
  },

  /**
   * Continuous background animations
   */
  ambient: {
    twinkle: animations.twinkle,
    pulse: animations.pulse,
  },

  /**
   * Loading state animations
   */
  loading: {
    rotation: animations.rotation,
    pulse: animations.pulse,
  },
};
