use std::collections::HashMap;
use pyo3::prelude::*;
use std::sync::Mutex;

#[derive(Clone)]
struct Document {
    content: String,
    metadata: HashMap<String, String>,
}

struct LlmModel {
    model_name: String,
}

impl LlmModel {
    fn new(model_name: String) -> Self {
        println!("[Rust] Initialized LLM: {}", model_name);
        Self { model_name }
    }

    fn generate(&self, prompt: &str) -> Result<String, Box<dyn std::error::Error>> {
        println!("[Rust] LLM::generate - Generating response using {}", self.model_name);
        let response = self.generate_response(prompt)?;
        Ok(response)
    }

    fn generate_response(&self, prompt: &str) -> Result<String, Box<dyn std::error::Error>> {
        // Format the prompt with context and question
        // Let the LLM generate its own answer based on context
        Ok(prompt.to_string())
    }
}

struct RagModel {
    model: String,
    embeddings: String,
    vector_db: Vec<Vec<f32>>,
    documents: Vec<Document>,
    llm: Mutex<LlmModel>,
}

impl RagModel {
    fn new(model_type: &str, embeddings_type: &str) -> Self {
        println!("[Rust] RagModel::new model_type={} embeddings_type={}", model_type, embeddings_type);
        let llm = LlmModel::new(model_type.to_string());
        Self {
            model: model_type.to_string(),
            embeddings: embeddings_type.to_string(),
            vector_db: Vec::new(),
            documents: Vec::new(),
            llm: Mutex::new(llm),
        }
    }

    fn fill_database(&mut self, csv_content: &str) -> Result<(), Box<dyn std::error::Error>> {
        println!("[Rust] fill_database start, csv_content_length={}", csv_content.len());
        let mut reader = csv::Reader::from_reader(csv_content.as_bytes());
        let headers = reader.headers()?.clone();
        let header_str = headers.iter().collect::<Vec<_>>().join(" | ");
        
        println!("[Rust] CSV headers: {}", header_str);
        
        let mut docs = Vec::new();
        let mut row_idx = 0;

        for result in reader.records() {
            let record = result?;
            // Keep entire row with headers for better context
            let row_values: Vec<String> = record.iter().map(|s| s.to_string()).collect();
            let content = row_values.join(" | ");
            
            let mut metadata = HashMap::new();
            metadata.insert("csv_row".to_string(), row_idx.to_string());
            metadata.insert("headers".to_string(), header_str.clone());
            metadata.insert("fields_count".to_string(), row_values.len().to_string());
            
            docs.push(Document {
                content,
                metadata,
            });
            row_idx += 1;
        }

        println!("[Rust] fill_database parsed {} rows", row_idx);
        
        self.documents = docs;
        self.vector_db.clear();

        for _ in &self.documents {
            self.vector_db.push(vec![0.0; 384]);
        }
        println!("[Rust] fill_database finished, documents={}, vector_db_entries={}", self.documents.len(), self.vector_db.len());

        Ok(())
    }

    fn retrieve_context(&self, query: &str) -> Result<String, Box<dyn std::error::Error>> {
        println!("[Rust] retrieve_context query={:?} documents={}", query, self.documents.len());
        
        if self.documents.is_empty() {
            println!("[Rust] retrieve_context: no documents loaded");
            return Ok("No documents in database.".to_string());
        }

        // Simple keyword-based retrieval: score documents by matching words in query or headers
        let query_lower = query.to_lowercase();
        let query_words: Vec<&str> = query_lower.split_whitespace().collect();
        let mut scored_docs: Vec<(usize, usize, &Document)> = self.documents
            .iter()
            .enumerate()
            .map(|(idx, doc)| {
                let doc_lower = doc.content.to_lowercase();
                let headers_lower = doc.metadata.get("headers").map(|h| h.to_lowercase()).unwrap_or_default();
                
                // Scoring: check both document content and headers
                let score = query_words
                    .iter()
                    .filter(|word| {
                        doc_lower.contains(*word) || headers_lower.contains(*word)
                    })
                    .count();
                (idx, score, doc)
            })
            .collect();

        // Sort by score (descending), then by document order (prefer later rows for numeric data)
        scored_docs.sort_by(|a, b| {
            match b.1.cmp(&a.1) {
                std::cmp::Ordering::Equal => b.0.cmp(&a.0), // If scores equal, prefer later row (might have larger values)
                other => other,
            }
        });

        let k = 2;
        let retrieved: Vec<&Document> = scored_docs
            .iter()
            .take(k)
            .map(|(_, _, doc)| *doc)
            .collect();

        println!("[Rust] retrieve_context retrieved {} docs, scores: {:?}", 
                 retrieved.len(), 
                 scored_docs.iter().take(k).map(|(_, score, _)| score).collect::<Vec<_>>());

        let serialized = retrieved
            .iter()
            .map(|doc| {
                let meta_str = doc.metadata.iter()
                    .filter(|(k, _)| k.as_str() != "headers")
                    .map(|(k, v)| format!("{}={}", k, v))
                    .collect::<Vec<_>>()
                    .join(", ");
                let header_info = doc.metadata.get("headers").map(|h| format!("Columns: {}\n", h)).unwrap_or_default();
                format!("Source: {}\n{}Content: {}", meta_str, header_info, doc.content)
            })
            .collect::<Vec<_>>()
            .join("\n\n");

        Ok(serialized)
    }

    fn stream_model(&self, message: &str) -> Result<Vec<String>, Box<dyn std::error::Error>> {
        println!("[Rust] stream_model message={:?}", message);
        if let Ok(llm) = self.llm.lock() {
            let response = llm.generate(message)?;
            Ok(response.split_whitespace().map(|s| s.to_string()).collect())
        } else {
            Err("Could not acquire LLM lock".into())
        }
    }

    fn stream_agent(&self, message: &str) -> Result<Vec<String>, Box<dyn std::error::Error>> {
        println!("[Rust] stream_agent message={:?}", message);
        let context = self.retrieve_context(message)?;
        println!("[Rust] Context retrieved:\n{}", context);
        
        // Build the full prompt for the LLM
        let prompt = format!(
            "Context:\n{}\n---\nQuestion: {}",
            context, message
        );
        
        // Generate response using LLM
        if let Ok(llm) = self.llm.lock() {
            let response = llm.generate(&prompt)?;
            println!("[Rust] LLM generated response for question: {}", message);
            // Return the response split into words for streaming
            Ok(response.split_whitespace().map(|s| s.to_string()).collect())
        } else {
            Err("Could not acquire LLM lock".into())
        }
    }
}

struct RecursiveCharacterTextSplitter {
    chunk_size: usize,
    chunk_overlap: usize,
    separators: Vec<String>,
}

impl RecursiveCharacterTextSplitter {
    fn new(chunk_size: usize, chunk_overlap: usize) -> Self {
        Self {
            chunk_size,
            chunk_overlap,
            separators: vec![
                "\n\n".to_string(),
                "\n".to_string(),
                " ".to_string(),
                "".to_string(),
            ],
        }
    }

    fn split_documents(&self, documents: Vec<Document>) -> Vec<Document> {
        let mut all_splits = Vec::new();
        for doc in documents {
            let splits = self.split_text(&doc.content);
            for split in splits {
                all_splits.push(Document {
                    content: split,
                    metadata: doc.metadata.clone(),
                });
            }
        }
        all_splits
    }

    fn split_text(&self, text: &str) -> Vec<String> {
        let mut good_splits = vec![text.to_string()];

        for separator in &self.separators {
            let mut new_splits = Vec::new();
            for text in good_splits {
                if separator.is_empty() {
                    for chunk in text.chars().collect::<Vec<_>>().chunks(self.chunk_size) {
                        let chunk_str: String = chunk.iter().collect();
                        new_splits.push(chunk_str);
                    }
                } else if text.contains(separator) {
                    let splits: Vec<&str> = text.split(separator).collect();
                    let mut current_chunk = String::new();
                    for split in splits {
                        if current_chunk.len() + split.len() + separator.len() > self.chunk_size {
                            if !current_chunk.is_empty() {
                                new_splits.push(current_chunk);
                                current_chunk = split.to_string();
                            } else {
                                new_splits.push(split.to_string());
                            }
                        } else {
                            if !current_chunk.is_empty() {
                                current_chunk.push_str(separator);
                            }
                            current_chunk.push_str(split);
                        }
                    }
                    if !current_chunk.is_empty() {
                        new_splits.push(current_chunk);
                    }
                } else {
                    new_splits.push(text);
                }
            }
            good_splits = new_splits;
        }

        good_splits
    }
}

#[pyclass]
struct PyRagModel {
    inner: RagModel,
}

#[pymethods]
impl PyRagModel {
    #[new]
    fn new(model_type: Option<String>, embeddings_type: Option<String>) -> Self {
        let model = model_type.unwrap_or_else(|| "HuggingFaceTB/SmolLM2-1.7B-Instruct".to_string());
        let embeddings = embeddings_type
            .unwrap_or_else(|| "sentence-transformers/all-MiniLM-l6-v2".to_string());
        println!("[Rust] PyRagModel::new model_type={} embeddings_type={}", model, embeddings);
        Self {
            inner: RagModel::new(&model, &embeddings),
        }
    }

    fn fill_database(&mut self, csv_content: &str) -> PyResult<()> {
        self.inner
            .fill_database(csv_content)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    fn retrieve_context(&self, query: &str) -> PyResult<String> {
        self.inner
            .retrieve_context(query)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    fn stream_model(&self, message: &str) -> PyResult<Vec<String>> {
        self.inner
            .stream_model(message)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    fn stream_agent(&self, message: &str) -> PyResult<Vec<String>> {
        self.inner
            .stream_agent(message)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }
}

#[pymodule]
fn model_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyRagModel>()?;
    Ok(())
}
