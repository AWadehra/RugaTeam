export type KnowledgeDocument = {
    // Manual fields 
    file_id: string;
    original_path: string;
    file_type: string;
    content_hash: string;
    title: string;
    chunk_no: number;
    creation_date: string;
    last_modified_date: string;
    possible_duplicate: boolean;
    reviewed_by_human: boolean;
    llm_model: string;
    extracted_at: string;
    
    // LLM-generated fields 
    suggested_filename: string;
    categories: string;
    authors: string[];
    topics: string[];
    tags: string[];
    summary: string;
    glossary_terms: string[];
}


