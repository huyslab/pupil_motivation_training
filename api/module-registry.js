// A module is a collection of tasks to be completed in a single sitting.
// Each module can contain one or more tasks, and each task can have its own configuration settings.

export const ModuleRegistry = {
    screening: {
        name: "Screening Module",
        moduleConfig: { // Settings that apply to all tasks in the module unless overridden
            session: "screening",
            sequence: "screening"
        }, 
        elements: [
            { type: "instructions", config: { text: "start_message" } },
            { type: "task", name: "max_press_test" },
            { type: "task", name: "vigour" },
            { type: "task", name: "acceptability_judgment", config: { task_name: "vigour", game_description: "piggy-bank game" } },
            { type: "instructions", config: { text: "end_message" } }
        ]
    }
};

