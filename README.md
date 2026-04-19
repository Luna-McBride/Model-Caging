# Model-Caging (PAUSED)
This project is meant to test the strength of a model with RAG retrieval while the model is caged. The end goal of the experiement is to see how well the strengths of an LLM can be highlighted without showing the major risks I've seen from models in my Prompt Engineering work, such as spitting out PII without asking.

The end expected behavior is to take in a CSV, have the model able to make specific changes based on a dropdown list of actions and column names (breaking up a column, combining a column, finding the top n, and similar tasks depending on the outcome), then ending with the final CSV being able to be saved. 

Current status:

- The experiment is paused after adding Rust showed the model and RAG setup could not be handled by my system even with the processing being handled in the fastest language available.

- Failed experimentation with Cython and Numba/JIT showed that Python was too slow to handle this use case on my machine. The point is to use Langchain with RAG, so PyTorch Lightning was unapplicable for this experiment.

- Testing the result on Rust proved a Typescript version would not be strong enough either due to Rust a much faster language.

- Switched the system entirely from Windows to Linux Mint entirely for the large reduction in used memory at baseline (nothing else open, 17% vs 40%). This change allowed 1.7B to run in the first place, but it was still very slow even with Rust.

- The experiments being done also only include small questions and a very small CSV file. If it cannot handle it now, there is no way it can handle bigger experiments.

- I may return to this experiment when I have better resources to handle it (more money for cloud or better hardware). For now, I need to pause it.

Past Updates:

- The necessary infrastructure for testing the model has been applied to the Angular frontend (API connection, output streaming, CSV accepting).

- CSV file passing has been added, but putting it into the vector database has not been added yet. The hope is to take in the file and pass it through to the vector database without saving in an intermediary step (thus reducing storage needs and making the system more open to handle larger CSV files).

- A simpler CORS has been added, but it is not currently targeted for the specific links to the Angular frontend as errors kept popping up surrounding it on the CSV submission and model output streaming stages. More testing needs to be done to figure out the cause.

- Simple streaming from the base model has been implemented to ensure proper event processing. This is anticipated to change into a CSV change display with a couple rows as well as a section for outputs such as requests for the top n of a certain group, but that depends on if using the CSV for RAG works as anticipated.

Tools used (up to this point):

- Angular/Typescript (for a more reactive frontend without some risks that come with React hooks)

- Python/Flask (API communication between the Angular frontend and model components)

- Rust/Copilot Claude (The Langchain was sent to Rust using Copilot, as I am not strong in Rust is the point was to prove if the fastest language provided sufficient speedup)

- Langchain (model usage, streaming, and RAG infrastructure)

- FAISS (Vector database, mainly used for its ability to remain in-place and its open-source nature)

- SmolLM2-1.7B-Instruct (subject to change) (Base model, used for its open-source nature and reduced risk of spouting out PII without reason)

Constraints:

-  Cost: This is a project by one developer (who is also unemployed). The money isn't there to be thrown around, hence why this is relatively simple in scope.

-  Efficiency: The SmolLM2-1.7B was the smallest able to start answering some of the questions, but it is also larger than my system has been able to handle.

-  Time: Setting up the API and reloading the model from the start takes time, so the spinup needs to be fast enough to spin up quickly based on changes. 
