import torch
from transformers import AutoTokenizer, AutoModel

class EmbedMedical():

    """
        Given a single string of text, this embedding model uses a version of ClinicalBERT
        called Bio_ClinicalBERT. This embedding tool has been trained on medical data and has a 
        deep medical vocabulary.
    """

    def get_medical_embeddings(text):
        
    
        # create pre-trained ClinicalBERT model anem
        model = "emilyalsentzer/Bio_ClinicalBERT"

        # Load the tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(model)
        model = AutoModel.from_pretrained(model)

        # Tokenize and encode the text
        encoded_input = tokenizer(
            text,
            max_length = 300,
            padding=True,
            truncation=True,
            return_tensors='pt' # return pytorch tensor
        )

        # Get the model outputs
        with torch.no_grad():
            output = model(**encoded_input)

        # Access the 'last_hidden_state' attribute to get the embeddings
        embedding = output.last_hidden_state[0, 0, :].numpy()
         

        # 'embeddings' 
        return embedding
