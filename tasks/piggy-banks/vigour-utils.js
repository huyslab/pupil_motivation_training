// Import functions 
import { postToParent, saveDataREDCap, updateBonusState, updateState, showTemporaryWarning, kickOut, fullscreen_prompt } from '@utils/index.js';
import { shakePiggy, updatePiggyTails} from "./utils.js";

// Reward/effort conditions: a full factorial of magnitude x fixed-ratio (FR).
// magnitude is the coin value (pence); ratio is the fixed ratio (presses per reward).
// 2 magnitudes x 3 ratios = 6 conditions.
const VIGOUR_MAGNITUDES = [1, 5];
const VIGOUR_RATIOS = [1, 5, 10];
const VIGOUR_CONDITIONS = VIGOUR_MAGNITUDES.flatMap(
  magnitude => VIGOUR_RATIOS.map(ratio => ({ magnitude, ratio }))
);

// Click-phase duration is sampled uniformly within this range (ms) per trial,
// freshly per participant (not frozen), matching the Python uniform(4.0, 6.0) s.
const VIGOUR_TRIAL_DURATION_RANGE_MS = [4000, 6000];

// Default number of blocks; one trial per condition per block. Overridable via
// the `n_blocks` task-registry option.
const VIGOUR_DEFAULT_N_BLOCKS = 3;

// Totals for periodic data saving, set when the timeline is built.
let vigourTotalTrials = 0;
let vigourSaveInterval = 1;

// Extract unique piggy bank parameters for UI configuration
const magnitudes = [...new Set(VIGOUR_CONDITIONS.map(c => c.magnitude))].sort((a, b) => a - b);
const ratios = [...new Set(VIGOUR_CONDITIONS.map(c => c.ratio))].sort((a, b) => b - a);

/**
 * Builds the full trial list: in each block the five conditions appear once in a
 * fresh random order, each with an independently sampled click duration. The
 * randomisation and durations are drawn at build time, so they differ per
 * participant rather than being frozen.
 * @param {number} nBlocks - number of blocks (one trial per condition per block)
 * @returns {Array<Object>} trial list with magnitude, ratio, trialDuration, block
 */
function buildVigourTrials(nBlocks) {
  const [minMs, maxMs] = VIGOUR_TRIAL_DURATION_RANGE_MS;
  const sampleDuration = () => Math.round(minMs + Math.random() * (maxMs - minMs));
  const shuffle = (arr) => {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };

  const trials = [];
  for (let block = 1; block <= nBlocks; block++) {
    shuffle(VIGOUR_CONDITIONS).forEach(cond => {
      trials.push({
        magnitude: cond.magnitude,
        ratio: cond.ratio,
        trialDuration: sampleDuration(),
        block: block
      });
    });
  }
  return trials;
}

// Global task state tracking variables
let taskTotalReward = 0;
let taskTotalPresses = 0;
let trialState = {
  trialPresses: 0,
  trialReward: 0,
  responseTime: []
};

// Array of image paths to preload for the vigour task
const VIGOUR_PRELOAD_IMAGES = [
        "1p-num.png", "2p-num.png", "5p-num.png", "10p-num.png", "piggy-bank.png", 
        "ooc_2p.png", "piggy-tail2.png", "saturate-icon.png", "tail-icon.png"
      ].map(s => "./assets/images/piggy-banks/" + s);

/**
 * Creates and animates a falling coin when user earns a reward
 * @param {number} magnitude - The coin value (determines which coin image to show)
 * @param {boolean} persist - Whether to use persistent coin container (default: false)
 */
function dropCoin(magnitude, persist = false) {
  const containerType = persist ? 'persist-coin-container' : 'coin-container';
  const coinContainer = document.getElementById(containerType);
  const coin = createCoin(magnitude);
  coinContainer.appendChild(coin);

  const animationOptions = getCoinAnimationOptions(magnitude);
  coin.animate(animationOptions.keyframes, animationOptions.config)
    .onfinish = () => coin.remove();
}

/**
 * Creates a coin image element with appropriate source and styling
 * @param {number} magnitude - The coin value
 * @returns {HTMLImageElement} Coin image element
 */
function createCoin(magnitude) {
  const coin = document.createElement('img');
  coin.className = 'vigour_coin';
  coin.src = magnitude === 0 ? './assets/images/piggy-banks/ooc_2p.png' : `./assets/images/piggy-banks/${magnitude}p-num.png`;
  coin.alt = `Coin of value ${magnitude}`;
  return coin;
}

/**
 * Returns animation configuration for coin drop effect
 * @param {number} magnitude - The coin value (affects animation duration)
 * @returns {Object} Animation keyframes and configuration
 */
function getCoinAnimationOptions(magnitude) {
  const duration = magnitude === 0 ? 2500 : 1000;
  const topStart = '-15%';
  const opacityStart = 0.8;

  return {
    keyframes: [
      { top: topStart, opacity: opacityStart, offset: 0 },
      { top: '70%', opacity: 1, offset: 0.1 },
      { top: '70%', opacity: 1, offset: 0.9 },
      { top: '70%', opacity: 0, offset: 1 }
    ],
    config: {
      duration: duration,
      easing: 'ease-in-out'
    }
  };
}

/**
 * Sets up a ResizeObserver to monitor element size changes
 * @param {string} elementId - ID of element to observe
 * @param {Function} callback - Function to call when element resizes
 */
function observeResizing(elementId, callback) {
  const resizeObserver = new ResizeObserver(callback);
  const element = document.getElementById(elementId);
  if (element) {
    resizeObserver.observe(element);
  }
}

/**
 * Creates a persistent coin container that survives trial transitions
 * Used to show coin animations across different trial screens
 */
function createPersistentCoinContainer() {
  // Check if it already exists
  if (document.getElementById('persist-coin-container')) {
    return;
  }
  
  // Create the container
  const persistContainer = document.createElement('div');
  persistContainer.id = 'persist-coin-container';
  document.body.appendChild(persistContainer);
  
  // Initialize position
  updatePersistentCoinContainer();
}

/**
 * Removes the persistent coin container from the DOM
 */
function removePersistentCoinContainer() {
  const persistContainer = document.getElementById('persist-coin-container');
  if (persistContainer) {
    persistContainer.remove();
  }
}

/**
 * Updates the position and size of persistent coin container to match the trial coin container
 * Ensures coin animations appear in the correct location
 */
function updatePersistentCoinContainer() {
  const coinContainer = document.getElementById('coin-container');
  const persistCoinContainer = document.getElementById('persist-coin-container');

  if (coinContainer && persistCoinContainer) {
    const rect = coinContainer.getBoundingClientRect();
    persistCoinContainer.style.top = `${rect.top}px`;
    persistCoinContainer.style.left = `${rect.left}px`;
    persistCoinContainer.style.width = `${rect.width}px`;
    persistCoinContainer.style.height = `${rect.height}px`;
  }
}

/**
 * Generates the HTML stimulus for a vigour trial with styled piggy bank
 * @param {number} magnitude - The reward magnitude (affects tail count)
 * @param {number} ratio - The response ratio requirement (affects color saturation)
 * @returns {string} HTML string for the trial stimulus
 */
function generateTrialStimulus(magnitude, ratio) {
  const ratio_index = ratios.indexOf(ratio);
  // Calculate saturation based on ratio - higher ratios = more saturated colors
  const ratio_factor = ratio_index / (ratios.length - 1);
  const piggy_style = `filter: saturate(${50 * (400 / 50) ** ratio_factor}%) brightness(${115 * (90 / 115) ** ratio_factor}%);`;
  return `
    <div class="experiment-wrapper">
      <!-- Middle Row (Piggy Bank & Coins) -->
      <div id="experiment-container">
        <div id="coin-container"></div>
        <div id="piggy-container">
          <!-- Piggy Bank Image -->
          <img id="piggy-bank" src="./assets/images/piggy-banks/piggy-bank.png" alt="Piggy Bank" style="${piggy_style}">
        </div>
      </div>
    </div>
  `;
}

// Global trial tracking variables
let vigourTrialCounter = 0;
let fsChangeHandler = null;

// --- Held-key response mechanism (matches the Python pupillometry task) ---
// Participants keep three keys (F, T, H) held down and tap a response key with
// the little finger: X for left-handers, M for right-handers. A press is only
// counted when all three hold keys are down at the moment of the tap.
const HOLD_KEYS = ['f', 't', 'h'];
let vigourResponseKey = 'x'; // set by the handedness prompt (x = left, m = right)

// Physical key state must be tracked continuously, because participants keep the
// hold keys (F, T, H) down across trials and never re-press them at trial start.
// A persistent, document-level tracker mirrors the Python task's GetAsyncKeyState
// approach: keydown/keyup keep `heldKeys` in sync for the whole task, and each
// trial only swaps in its own response callbacks. (Rebuilding the set per trial
// left it empty until the OS key-repeat re-fired, causing spurious warnings.)
const heldKeys = new Set();
let keyTrackingInstalled = false;
let activeHoldHandlers = null; // { onValidPress, onHoldViolation } for the current trial

/** Installs the persistent key-state tracker once for the whole task. */
function installKeyStateTracking() {
  if (keyTrackingInstalled) return;
  keyTrackingInstalled = true;

  document.addEventListener('keydown', (e) => {
    const key = e.key.toLowerCase();
    const alreadyHeld = heldKeys.has(key);
    heldKeys.add(key);

    if (!activeHoldHandlers || key !== vigourResponseKey) return;
    // Ignore OS auto-repeat and a response key that is still held down, so each
    // physical tap counts once (equivalent to allow_held_key: false).
    if (e.repeat || alreadyHeld) return;

    if (!HOLD_KEYS.every(k => heldKeys.has(k))) {
      if (activeHoldHandlers.onHoldViolation) activeHoldHandlers.onHoldViolation();
      return;
    }
    activeHoldHandlers.onValidPress(e);
  });

  document.addEventListener('keyup', (e) => {
    heldKeys.delete(e.key.toLowerCase());
  });
}

/**
 * Routes response-key taps for the current trial to the given callbacks. The
 * underlying key-state tracker is shared, so held keys carry over between trials.
 * @param {Object} handlers
 * @param {Function} handlers.onValidPress - called when the response key is tapped while all hold keys are down
 * @param {Function} [handlers.onHoldViolation] - called when the response key is tapped without all hold keys down
 */
function attachHoldKeyListeners({ onValidPress, onHoldViolation }) {
  installKeyStateTracking();
  activeHoldHandlers = { onValidPress, onHoldViolation };
}

/** Stops routing taps to the current trial's callbacks (tracker stays installed). */
function detachHoldKeyListeners() {
  activeHoldHandlers = null;
}

/**
 * Handedness prompt: a Left/Right button selection that sets the little-finger
 * response key (X for left hand, M for right hand) used throughout the task.
 * @returns {Object} jsPsych trial object
 */
function vigourHandednessTrial() {
  return {
    type: jsPsychHtmlButtonResponse,
    stimulus: `
      <div id="instruction-text" style="font-size: 1.2em; line-height: 1.6;">
        <p>Which hand do you write with?</p>
      </div>
    `,
    choices: ['Left', 'Right'],
    data: { trialphase: 'vigour_handedness' },
    on_load: function () {
      // Start tracking physical key state from the very start of the vigour
      // task, so F/T/H presses are registered even before the practice demo.
      installKeyStateTracking();
    },
    on_finish: function (data) {
      // Button index 0 = Left (X), 1 = Right (M).
      vigourResponseKey = data.response === 1 ? 'm' : 'x';
      data.handedness = vigourResponseKey === 'm' ? 'right' : 'left';
      data.response_key = vigourResponseKey;
      data.hold_keys = HOLD_KEYS.join(',');
    }
  };
}

/** Returns the response-key letter to show participants ('X' or 'M'). */
function getResponseKeyLabel() {
  return vigourResponseKey.toUpperCase();
}

/** Returns the chosen handedness ('left' or 'right'). */
function getHandednessLabel() {
  return vigourResponseKey === 'm' ? 'right' : 'left';
}

/**
 * Creates a single vigour trial with piggy bank shaking mechanics
 * @param {Object} settings - Configuration object containing task parameters
 * @returns {Object} jsPsych trial object
 */
function piggyBankTrial(settings) {
  return {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: function () {
      return generateTrialStimulus(jsPsych.evaluateTimelineVariable('magnitude'), jsPsych.evaluateTimelineVariable('ratio'));
    },
    choices: 'NO_KEYS',
    // response_ends_trial: false,
    trial_duration: jsPsych.timelineVariable('trialDuration'),
    save_timeline_variables: ["magnitude", "ratio", "block"],
    data: {
      trialphase: 'vigour_trial',
      trial_duration: jsPsych.timelineVariable('trialDuration'),
      // Trial-specific data functions
      responseTime: () => { return trialState.responseTime },
      trial_presses: () => { return trialState.trialPresses },
      trial_reward: () => { return trialState.trialReward },
      // Global task data
      total_presses: function() { return taskTotalPresses },
      total_reward: function() { return taskTotalReward }
    },
    on_start: function (trial) {
      // Shorten trial duration for simulation mode
      if (window.simulating) {
        trial.trial_duration = 500;
      }

      // Reset trial state
      trialState = {
        trialPresses: 0,
        trialReward: 0,
        responseTime: []
      };
      
      // Store trial state in trial data for access by data functions
      trial.data.trialState = trialState;

      let lastPressTime = 0;
      let pressCount = 0;
      let lastHoldWarningTime = 0;

      const ratio = jsPsych.evaluateTimelineVariable('ratio');
      const magnitude = jsPsych.evaluateTimelineVariable('magnitude');
      const listenerStart = performance.now();

      // Count taps of the little-finger response key, but only while the three
      // hold keys (F, T, H) are held down. See attachHoldKeyListeners above.
      attachHoldKeyListeners({
        onValidPress: function () {
          const rt = performance.now() - listenerStart;
          trialState.responseTime.push(rt - lastPressTime);
          lastPressTime = rt;
          shakePiggy();
          pressCount++;
          trialState.trialPresses++;
          taskTotalPresses++;

          // Check if ratio requirement is met for reward
          if (pressCount === ratio) {
            trialState.trialReward += magnitude;
            taskTotalReward += magnitude;
            pressCount = 0;
            dropCoin(magnitude, true);
          }
        },
        onHoldViolation: function () {
          // Faithful to the Python task: ignore the press and remind the
          // participant to keep the three keys held. Throttled to avoid spam.
          const now = performance.now();
          if (now - lastHoldWarningTime > 1500) {
            lastHoldWarningTime = now;
            showTemporaryWarning("Keep holding 'F', 'T', and 'H'", 800);
          }
        }
      });
    },
    on_load: function () {
      const currentMag = jsPsych.evaluateTimelineVariable('magnitude');
      const currentRatio = jsPsych.evaluateTimelineVariable('ratio');

      // Add magnitudes and ratios to settings for piggy tails
      settings.magnitudes = magnitudes;
      settings.ratios = ratios;

      updatePiggyTails(currentMag, currentRatio, settings);
      updatePersistentCoinContainer(); // Update the persistent coin container
      observeResizing('coin-container', updatePersistentCoinContainer);

      // Add fullscreen change listener to re-update piggy tails
      fsChangeHandler = () => {
        if (document.fullscreenElement || document.webkitFullscreenElement) {
          updatePiggyTails(currentMag, currentRatio, settings);
        }
      };
      document.addEventListener('fullscreenchange', fsChangeHandler);
      document.addEventListener('webkitfullscreenchange', fsChangeHandler);

      // Simulate keypresses for testing mode: hold the three keys, then tap the
      // response key. Events are dispatched on document so the held-key
      // listeners pick them up.
      if (window.simulating) {
        const trial_presses = jsPsych.randomization.randomInt(1, 8);
        const avg_rt = 500 / trial_presses;
        HOLD_KEYS.forEach(k => document.dispatchEvent(new KeyboardEvent('keydown', { key: k })));
        for (let i = 0; i < trial_presses; i++) {
          jsPsych.pluginAPI.setTimeout(() => {
            document.dispatchEvent(new KeyboardEvent('keydown', { key: vigourResponseKey }));
            document.dispatchEvent(new KeyboardEvent('keyup', { key: vigourResponseKey }));
          }, avg_rt * i + 1);
        }
        jsPsych.pluginAPI.setTimeout(() => {
          HOLD_KEYS.forEach(k => document.dispatchEvent(new KeyboardEvent('keyup', { key: k })));
        }, 500);
      }
    },
    on_finish: function (data) {
      // Clean up listeners
      detachHoldKeyListeners();
      jsPsych.pluginAPI.cancelAllKeyboardResponses();
      vigourTrialCounter += 1;
      data.trial_number = vigourTrialCounter;
      
      // Save data at regular intervals and end of task
      if ((vigourSaveInterval > 0 && vigourTrialCounter % vigourSaveInterval === 0) || vigourTrialCounter === vigourTotalTrials) {
        saveDataREDCap(3);
        updateBonusState(settings);
      }
      
      // Clean up fullscreen event listeners
      if (fsChangeHandler) {
        document.removeEventListener('fullscreenchange', fsChangeHandler);
        document.removeEventListener('webkitfullscreenchange', fsChangeHandler);
        fsChangeHandler = null;
      }

      // Show warning for no response on easy trials
      if (data.trial_presses === 0 && data.timeline_variables.ratio === 1) {
        var up_to_now = parseInt(jsPsych.data.get().last(1).select('n_warnings').values);
        jsPsych.data.addProperties({
          n_warnings: up_to_now + 1
        });
        // console.log(jsPsych.data.get().last(1).select('n_warnings').values[0]);
        showTemporaryWarning("Didn't catch a response - moving on", 800); // Enable this line for non-stopping warning
      }
      
      // Clean up trial state reference
      delete data.trialState;
    }
  }
};

/**
 * Creates the complete timeline for the vigour task core trials
 * @param {Object} settings - Configuration object containing task parameters
 * @returns {Array} Array of jsPsych timeline objects for all vigour trials
 */
function createVigourCoreTimeline(settings) {
    let experimentTimeline = [];

    // Number of blocks is configurable; one trial per condition per block.
    const nBlocks = (settings && Number.isInteger(settings.n_blocks) && settings.n_blocks > 0)
        ? settings.n_blocks
        : VIGOUR_DEFAULT_N_BLOCKS;
    const trials = buildVigourTrials(nBlocks);
    vigourTotalTrials = trials.length;
    vigourSaveInterval = Math.max(1, Math.round(vigourTotalTrials / 3));

    // Create a timeline for each trial with kick-out and fullscreen checks
    trials.forEach(trial => {
        experimentTimeline.push({
            timeline: [kickOut(settings), fullscreen_prompt, piggyBankTrial(settings)],
            timeline_variables: [trial]
        });
    });

    // Add initialization callback to first trial
    experimentTimeline[0]["on_timeline_start"] = () => {
        updateState("no_resume_10_minutes");
        updateState(`vigour_task_start`);
        createPersistentCoinContainer();
        // Reset task counters
        taskTotalReward = 0;
        taskTotalPresses = 0;
    };

    // Add cleanup callback to last trial
    experimentTimeline.at(-1)["on_timeline_finish"] = () => {
        removePersistentCoinContainer();
    };

    return experimentTimeline;
}

export {
  createVigourCoreTimeline,
  updatePersistentCoinContainer,
  observeResizing,
  dropCoin,
  VIGOUR_PRELOAD_IMAGES,
  vigourHandednessTrial,
  attachHoldKeyListeners,
  detachHoldKeyListeners,
  getResponseKeyLabel,
  getHandednessLabel,
  HOLD_KEYS
}