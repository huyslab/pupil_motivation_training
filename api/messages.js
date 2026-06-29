
/**
 * RELMED Task Battery - Messages Module
 * 
 * This module contains standardized messages and instructions displayed to participants
 * during different phases of the RELMED experiment sessions. It includes:
 * 
 * - Start and end messages for different session types (full_battery, screening)
 * - Formatted warning messages for response timeouts
 * - Dynamic content based on session settings (e.g., week 0 vs other weeks)
 * 
 * The messages support HTML formatting and can include optional fields passed on to the jsPsych instructions trial object.
 */

import { endExperiment } from '@utils/index.js';

const formatted_warning_msg = `
    <div id='vigour-warning-temp' style="
    background-color: rgba(244, 206, 92, 0.9);
    padding: 15px 25px;
    border-radius: 8px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 24px;
    font-weight: 500;
    color: #182b4b;
    transition: opacity 0.2s ease;
    text-align: center;
    letter-spacing: 0.0px;
    ">Didn't catch a response - moving on</div>
`;


export const messages = {
    living_lab: {
        start_message: (settings) => {
            return [`<p><b>Thank you for taking part in this part of the study!</b></p>
                <p>The purpose of this part is to examine how people learn from positive and negative feedback while playing games.
                <p>You will play a few simple trial-and-error learning games. Your goal in each game is to win as many coins as possible.</p>
                <p>The games may feel a bit fast-paced because we're interested in your quick, intuitive decisions. Since they're designed around learning from experience, making mistakes is completely expected. Over time, you'll figure out better choices and improve your performance.</p>
                `,
                `
                <p>If at some point you are taking too long to respond, you might see a message like this:</p><br>
                ${formatted_warning_msg}
                <br><p>It is perfectly natural to take a bit longer when you are learning something new. However, if you see this message a few times, it may be a sign that you are overthinking your choices.</p>
                <p>If at any point you feel like you need some assistance, you can find our contact details by pressing the question mark in the top right corner. We are happy to help.</p>`
            ];
        }
    },
    full_battery: {
        start_message: (settings) => { 
            return [`<p><b>Thank you for taking part in this session!</b></p>
                <p>The purpose of this session is to examine how people learn from positive and negative feedback while playing games.
                <p>You will play a few simple trial-and-error learning games. Your goal in each game is to win as many coins as possible.</p>
                <p>The games may feel a bit fast-paced because we're interested in your quick, intuitive decisions. Since they're designed around learning from experience, making mistakes is completely expected. Over time, you'll figure out better choices and improve your performance.</p>
                ` + (settings.session === "wk0" ?  `<b>Please read the instructions carefully. They may differ from the training session.</b>` : ""),
                `
                <p>If at some point you are taking too long to respond, you might see a message like this:</p><br>
                ${formatted_warning_msg}
                <br><p>It is perfectly natural to take a bit longer when you are learning something new. However, if you see this message a few times, it may be a sign that you are overthinking your choices.</p>
                <p>If at any point you feel like you need some assistance, you can find our contact details by pressing the question mark in the top right corner. We are happy to help.</p>`
            ];
        },
        break_message: {
            message: `<p>You can now take a short break.</p><p>Please ring the bell when you are ready to continue.</p>`,
            key_forward: 'c',
            show_clickable_nav: false
        }
    },
    screening: {
        start_message: [
            `<p><b>Welcome!</b></p>
            <p>This is a short training session to prepare you for the lab experiment you will take part in.</p>
            <p>You will practise a game that is similar to one of the tasks you will play in the lab. Your goal is to win as many coins as possible.</p>
            <p>The game may feel a bit fast-paced because we're interested in your quick, intuitive responses. It is designed around learning from experience, so making mistakes is completely expected, and it is fine to take a little while to get the hang of it.</p>
            `,
            `
            <p>If at some point you are taking too long to respond, you might see a message like this:</p><br>
            ${formatted_warning_msg}
            <br><p>It is perfectly natural to take a bit longer when you are learning something new. However, if you see this message a few times, it may be a sign that you are overthinking your choices.</p>
            <p>If at any point you feel like you need some assistance, you can find our contact details by pressing the question mark in the top right corner. We are happy to help.</p>`
        ],
        end_message: {
            message: `<p>Thank you for completing this session!</p>
                <p>Please call the experimenter.</p>`,
            on_start: endExperiment
        },
    }
}

