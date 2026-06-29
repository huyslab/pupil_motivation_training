import { createVigourCoreTimeline, VIGOUR_PRELOAD_IMAGES, vigourHandednessTrial, vigourCuePreloadAudio, resolveVigourNBlocks, getVigourCueMapping } from './vigour-utils.js';
import { vigour_instructions, headphoneInstruction, vigour_end_message } from './vigour-instructions.js';
import { createPreloadTrial } from '../../core/utils/index.js';

/**
 * Creates the complete timeline for the vigour task (piggy bank shaking)
 * @param {Object} settings - Configuration object containing task parameters
 * @returns {Array} Array of jsPsych timeline objects for the vigour task
 */
export function createVigourTimeline(settings) {
    // Determine (and log) the participant's cue -> piggy-bank mapping at load time.
    getVigourCueMapping();

    const vigourTimeline = [
        // Preload all images and cue sounds required for the vigour task
        createPreloadTrial(
            VIGOUR_PRELOAD_IMAGES,
            settings.task_name,
            vigourCuePreloadAudio(resolveVigourNBlocks(settings))
        ),
        // Ask handedness up front so all instructions and trials use the
        // correct little-finger response key (X for left, M for right).
        vigourHandednessTrial(),
        // General "put your headphones on" reminder, before the task is explained.
        headphoneInstruction,
        // Interactive instructions; these end with the piggy-bank sound message
        // and volume calibration, right before the task begins.
        vigour_instructions,
        // Run the main vigour task trials (spread to flatten the array)
        ...createVigourCoreTimeline(settings),
        // Closing message: the lab task is similar and pays a coin-based bonus.
        vigour_end_message,
    ];

    return vigourTimeline;
}