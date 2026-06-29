import { createVigourCoreTimeline, VIGOUR_PRELOAD_IMAGES, vigourHandednessTrial, vigourCuePreloadAudio, resolveVigourNBlocks } from './vigour-utils.js';
import { vigour_instructions } from './vigour-instructions.js';
import { createPreloadTrial } from '../../core/utils/index.js';

/**
 * Creates the complete timeline for the vigour task (piggy bank shaking)
 * @param {Object} settings - Configuration object containing task parameters
 * @returns {Array} Array of jsPsych timeline objects for the vigour task
 */
export function createVigourTimeline(settings) {
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
        // Show interactive instructions with practice demo
        vigour_instructions,
        // Run the main vigour task trials (spread to flatten the array)
        ...createVigourCoreTimeline(settings),
    ];

    return vigourTimeline;
}