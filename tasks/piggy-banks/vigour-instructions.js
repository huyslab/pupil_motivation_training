import { updatePersistentCoinContainer, observeResizing, dropCoin, attachHoldKeyListeners, detachHoldKeyListeners, getResponseKeyLabel, getHandednessLabel } from './vigour-utils.js';
import { shakePiggy } from './utils.js';
import { updateState, showTemporaryWarning } from '@utils/index.js';

/**
 * Interactive instruction page that demonstrates the piggy bank shaking mechanism
 * Allows users to practice the task with immediate feedback
 */
const instructionPage = {
  type: jsPsychHtmlKeyboardResponse,
  stimulus: generateInstructStimulus,
  choices: ["NO_KEYS"],
  trial_duration: null,
  data: {trialphase: 'vigour_instructions'},
  on_load: function () {
    updatePersistentCoinContainer();
    observeResizing('coin-container', updatePersistentCoinContainer);

    // Demo state variables
    let shakeCount = 0;
    let FR = 5; // Fixed ratio - reward every 5 presses
    let timerStarted = false;
    let timer;
    updateInstructionText(shakeCount);
    const bottomContainer = document.getElementById('bottom-container');
    const experimentContainer = document.getElementById('experiment-container');
    const buttonInstruction = document.getElementById('button-instruction');
    let lastHoldWarningTime = 0;
    attachHoldKeyListeners({ onValidPress: handleResponse, onHoldViolation: warnHold });

    /**
     * Warns (throttled) when the response key is tapped without the three hold
     * keys held down.
     */
    function warnHold() {
      const now = performance.now();
      if (now - lastHoldWarningTime > 1500) {
        lastHoldWarningTime = now;
        showTemporaryWarning("Keep holding 'F', 'T', and 'H'", 800);
      }
    }

    /**
     * Handles a valid response-key tap during the instruction demo
     * Provides immediate feedback and coin rewards
     */
    function handleResponse() {
      shakeCount++;
      shakePiggy();
      updateInstructionText(shakeCount);

      // Give coin reward every FR presses
      if (shakeCount % FR === 0) {
        dropCoin(0);
      }

      // Show continue/restart options after first reward
      if (shakeCount === FR + 1) {
        bottomContainer.style.visibility = 'visible';

        if (!timerStarted) {
          timerStarted = true;
          startTimer();
        }
      }
    }

    /**
     * Starts timer to highlight the continue button after 10 seconds
     */
    function startTimer() {
      timer = setTimeout(() => {
        experimentContainer.style.visibility = 'hidden';
        // buttonInstruction.style.fontSize = '1.5em';
        buttonInstruction.style.color = '#0066cc';
      }, 10000); // 10 seconds
    }

    /**
     * Resets the instruction demo to initial state
     */
    function restart() {
      shakeCount = 0;
      timerStarted = false;
      clearTimeout(timer);
      updateInstructionText(shakeCount);
      experimentContainer.style.visibility = 'visible';
      bottomContainer.style.visibility = 'hidden';
      buttonInstruction.style.fontSize = '';
      buttonInstruction.style.color = '';
      detachHoldKeyListeners();
      attachHoldKeyListeners({ onValidPress: handleResponse, onHoldViolation: warnHold });
      const coinContainer = document.getElementById('coin-container');
      coinContainer.innerHTML = '';
    }

    // Set up button event listeners
    document.getElementById('restart-button').addEventListener('click', restart);
    document.getElementById('continue-button').addEventListener('click', jsPsych.finishTrial);

    // Simulate user interaction for testing mode
    if (window.simulating) {
      async function simulateKeyPressesAndClick() {
        const responseKey = getResponseKeyLabel().toLowerCase();
        // Hold the three keys down for the whole demo.
        ['f', 't', 'h'].forEach(k => document.dispatchEvent(new KeyboardEvent('keydown', { key: k })));

        const pressKeyPromises = [];
        // Simulate FR + 1 valid taps to trigger coin drop and continue option
        for (let i = 0; i < FR + 1; i++) {
          const scheduledTime = 100 * i + 1; // Delay for this specific tap
          pressKeyPromises.push(
            new Promise(resolve => {
              setTimeout(() => {
                document.dispatchEvent(new KeyboardEvent('keydown', { key: responseKey }));
                document.dispatchEvent(new KeyboardEvent('keyup', { key: responseKey }));
                resolve();
              }, scheduledTime);
            })
          );
        }

        // Wait for all taps to be simulated
        await Promise.all(pressKeyPromises);
        ['f', 't', 'h'].forEach(k => document.dispatchEvent(new KeyboardEvent('keyup', { key: k })));

        // Simulate clicking continue button
        jsPsych.pluginAPI.clickTarget(document.getElementById('continue-button'), 100);
      }

      // Call the async function to start the simulation
      simulateKeyPressesAndClick();
    }
  },
  on_finish: function () {
    detachHoldKeyListeners();
    jsPsych.pluginAPI.cancelAllKeyboardResponses();
  }
};

/**
 * Static instruction pages explaining the game rules and coin types
 * Uses jsPsych instructions plugin with navigation
 */
const ruleInstruction = {
  type: jsPsychInstructions,
  data: {trialphase: 'vigour_instructions'},
  show_clickable_nav: true,
  pages: [`
  <div id="instruction-text" style="text-align: left">
    <p><strong>You will now play a few minutes of this game, collecting coins!</strong></p>
    
    <p>Throughout the game, you will see different piggy banks with unique appearances:</p>
    <ul>
        <li><img src="./assets/images/piggy-banks/saturate-icon.png" style="height:1.3em; transform: translateY(0.2em)"> <span class="highlight-txt">Vividness</span> of piggy colors: Indicates how fast you need to shake it.</li>
        <li><img src="./assets/images/piggy-banks/tail-icon.png" style="height:1.3em; transform: translateY(0.2em)"> <span class="highlight-txt">Tail length</span>: Longer piggy tails = more valuable coins.</li>
    </ul>
    </div>
    `,
    `<div id="instruction-text" style="text-align: left">
    <p>Types of coins you can win:</p>
    <div class="instruct-coin-container">
        <div class="instruct-coin">
            <img src="./assets/images/piggy-banks/1p-num.png" alt="1 Penny">
            <p>1 Penny</p>
        </div>
        <div class="instruct-coin">
            <img src="./assets/images/piggy-banks/2p-num.png" alt="2 Pence">
            <p>2 Pence</p>
        </div>
        <div class="instruct-coin">
            <img src="./assets/images/piggy-banks/5p-num.png" alt="5 Pence">
            <p>5 Pence</p>
        </div>
    </div>
    
    <p><span class="highlight-txt">Your bonus</span>: At the end of the game, we will pay you a proportion of the total amount of coins collected across all the piggy banks.</p>
    </div>
      `]
};

/**
 * Final confirmation screen before starting the actual vigour task
 * Allows user to restart instructions or begin the task
 */
const startConfirmation = {
  type: jsPsychHtmlKeyboardResponse,
  // Begin with the participant's response key, or 'r' to restart instructions.
  choices: () => [getResponseKeyLabel().toLowerCase(), 'r'],
  stimulus: function () {
    const label = getResponseKeyLabel();
    const hand = getHandednessLabel();
    return `
  <div id="instruction-text">
      <p>You will now play the piggy-bank game without a break for about <strong>four minutes</strong>.</p>
      <p>When you're ready, place your <strong>${hand} hand's index, middle and ring fingers</strong> on the <span class="spacebar-icon">F</span>, <span class="spacebar-icon">T</span> and <span class="spacebar-icon">H</span> keys and keep them <strong>held down</strong> throughout the game.</p>
      <p>Use the <strong>little finger of your ${hand} hand</strong> to tap the <span class="spacebar-icon">${label}</span> key, as shown below.</p>
      <img src="./assets/images/piggy-banks/vigour_key.png" style="width:250px;" alt="Key press illustration">
      <p>While holding the three keys, tap <span class="spacebar-icon">${label}</span> once to begin.</p>
      <p>If you want to start over from the beginning, press <span class="spacebar-icon">R</span>.</p>
  </div>
    `;
  },
  post_trial_gap: 300,
  data: {trialphase: 'vigour_instructions'},
  simulation_options: {
    data: {
      response: () => getResponseKeyLabel().toLowerCase()
    }
  },
  on_finish: function (data) {
    // Set RNG seed for reproducible trial sequences
    const seed = jsPsych.randomization.setSeed();
    data.rng_seed = seed;
  },
}

/**
 * Dedicated screen that explains the hold-and-tap response method before the
 * demo, introducing the two parts one step at a time. Adapts the tap key and
 * hand to the participant's handedness.
 * NOTE: vigour_key.png is a placeholder image (shows the old key) until the new
 * photo of the keys is added.
 */
const holdKeysInstruction = {
  type: jsPsychInstructions,
  data: {trialphase: 'vigour_instructions'},
  show_clickable_nav: true,
  pages: function () {
    const label = getResponseKeyLabel();
    const hand = getHandednessLabel();
    return [
      // Step 1: overview
      `
  <div id="instruction-text">
    <p><strong>How to shake a piggy bank</strong></p>
    <p>You will collect coins by shaking piggy banks.</p>
    <p>Shaking uses the keyboard in a special way. We'll go through it one step at a time.</p>
  </div>
      `,
      // Step 2: the holding part
      `
  <div id="instruction-text">
    <p><strong>Step 1: hold three keys down</strong></p>
    <p>Using your <strong>${hand} hand</strong>, place three fingers on the <span class="spacebar-icon">F</span>, <span class="spacebar-icon">T</span> and <span class="spacebar-icon">H</span> keys:</p>
    <p>your <strong>index, middle and ring fingers</strong>.</p>
    <p><strong>Hold all three keys down</strong>, and keep holding them the whole time you play.</p>
    <img src="./assets/images/piggy-banks/vigour_key.png" style="width:220px;" alt="Keys to hold">
  </div>
      `,
      // Step 3: the tapping part
      `
  <div id="instruction-text">
    <p><strong>Step 2: tap to shake</strong></p>
    <p>While you keep holding <span class="spacebar-icon">F</span>, <span class="spacebar-icon">T</span> and <span class="spacebar-icon">H</span>,</p>
    <p>tap the <span class="spacebar-icon">${label}</span> key with the <strong>little finger of your ${hand} hand</strong>.</p>
    <p>Each tap gives the piggy bank a shake. The more you tap, the more coins you get!</p>
    <img src="./assets/images/piggy-banks/vigour_key.png" style="width:220px;" alt="Key to tap">
  </div>
      `
    ];
  }
};

/**
 * Main export: Complete vigour task instruction timeline
 * Includes loop functionality to repeat instructions if user presses 'r'
 */
export const vigour_instructions = {
  timeline: [holdKeysInstruction, instructionPage, ruleInstruction, startConfirmation],
  // Loop function to repeat instructions if user presses 'r'
  loop_function: function (data) {
    const last_iter = data.last(1).values()[0];
    if (jsPsych.pluginAPI.compareKeys(last_iter.response, 'r')) {
      return true; // Repeat instructions
    } else {
      return false; // Continue to main task
    }
  },
  on_timeline_start: () => {updateState(`vigour_instructions_start`)}
}

/**
 * Generates the HTML stimulus for the interactive instruction page
 * @returns {string} HTML string containing the instruction demo interface
 */
function generateInstructStimulus() {
  return `
    <div class="experiment-wrapper">
      <!-- Upper Information (Instructions) -->
      <div id="instruction-container">
        <div id="instruction-text"></div>
      </div>

      <!-- Middle Row (Piggy Bank & Coins) -->
      <div id="experiment-container">
        <div id="coin-container"></div>
        <div id="piggy-container">
          <!-- Piggy Bank Image -->
          <img id="piggy-bank" src="./assets/images/piggy-banks/piggy-bank.png" alt="Piggy Bank">
        </div>
      </div>

      <!-- Lower Information (Buttons) -->
      <div id="bottom-container" style="visibility: hidden">
        <p id="button-instruction" style="margin: 24px">Press <span style="font-weight: bold;">Restart</span> to try again, or <span style="font-weight: bold;">Continue</span> to proceed.</p>
        <div id="button-container">
          <button id="restart-button" class="jspsych-btn">Restart</button>
          <button id="continue-button" class="jspsych-btn">Continue</button>
        </div>
      </div>
    </div>
  `;
}

/**
 * Updates the instruction text based on user's progress through the demo
 * @param {number} shakeCount - Number of times user has pressed the key
 */
function updateInstructionText(shakeCount) {
  const label = getResponseKeyLabel();
  const hand = getHandednessLabel();
  const holdKeys = `<span class="spacebar-icon">F</span>, <span class="spacebar-icon">T</span> and <span class="spacebar-icon">H</span>`;
  const messages = [
    `<p>Now try it yourself!</p><p>With your ${hand} hand, hold the ${holdKeys} keys down with your index, middle and ring fingers, then tap the <span class="spacebar-icon">${label}</span> key with your little finger to shake this piggy bank!</p>`,
    `<p>Keep holding ${holdKeys}, and tap <span class="spacebar-icon">${label}</span> with your little finger to shake the piggy bank!</p><p>Keep tapping to shake more...</p>`,
    '<p>Well done, You just got a coin out of the piggy bank!</p><p><span class="highlight-txt">You can always tap again for more coins.</span> Try getting some more!</p>'
  ];
  let messageIndex = 0;
  if (shakeCount < 1) {
    messageIndex = 0; // Initial welcome message
  } else if (shakeCount >= 1 && shakeCount < 5) {
    messageIndex = 1; // Encouragement to continue pressing
  } else {
    messageIndex = 2; // Success message after first coin
  }
  document.getElementById('instruction-text').innerHTML = messages[messageIndex];
}
