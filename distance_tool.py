import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
from scipy import stats

# Define urgent and non-urgent action phrases
urgent_phrases = [
    "I recommend you take this medicine immediately to address the symptoms.",
    "You should obtain a prescription for a painkiller for this condition.",
    "Please proceed to the pharmacy to pick up your prescribed medication.",
    "This requires prompt medical attention; take the prescribed medication as directed.",
    "I suggest an over-the-counter remedy from the pharmacy for symptomatic relief.",
    "It's advisable to start this treatment course as soon as possible.",
    "A strong analgesic is indicated for this level of discomfort.",
    "Visit your local pharmacy for an appropriate therapeutic solution.",
    "It's important to begin this medication regimen without undue delay.",
    "Consider a fast-acting pain reliever to manage acute pain.",
    "We need to initiate this treatment protocol promptly.",
    "I'll write you a prescription; please have it filled today.",
    "The clinical picture suggests immediate pharmacological intervention.",
    "For effective management, a course of [specific type of medication, e.g., antibiotics] is necessary.",
    "Let's get you started on a medication to alleviate these symptoms quickly.",
    "Given your presentation, I advise you to procure [medication name/type] from the chemist.",
    "Prompt administration of this medication is key to a swift recovery.",
    "This situation warrants the use of a targeted pharmaceutical agent.",
    "To prevent exacerbation, please adhere to this medication schedule strictly.",
    "I believe a prescription for [medication class] will be most beneficial at this juncture."
]

non_urgent_phrases = [
    "Oh, just wait a little while, and it should improve; let's adopt a conservative approach for now.",
    "You don't need to do anything specific right now; watchful waiting is appropriate.",
    "Let's observe the progression for a few days before considering intervention.",
    "This condition will likely resolve spontaneously; no active treatment is indicated at this time.",
    "I don't believe any pharmacological intervention is necessary at this stage.",
    "For now, let's just monitor the situation closely and reassess if symptoms change.",
    "Give it some time; the body often has a remarkable capacity to heal itself.",
    "No need for medication at this point; let's allow natural resolution.",
    "Rest and observe how you feel in a day or two; further action may not be required.",
    "At this moment, active treatment isn't clinically warranted.",
    "We'll maintain a period of observation; often, these symptoms are self-limiting.",
    "Current clinical guidelines suggest a non-interventional stance for this presentation.",
    "It's best to avoid unnecessary medication; let's see if it subsides naturally.",
    "I recommend we defer active treatment and re-evaluate in [timeframe, e.g., 48 hours].",
    "Many cases like this resolve without specific medical therapy.",
    "The symptoms are mild and don't necessitate immediate pharmaceutical intervention.",
    "Let's prioritize conservative management and see how things evolve.",
    "At this juncture, a 'wait-and-see' strategy is the most prudent course.",
    "Unless symptoms worsen significantly, no specific action is needed.",
    "We will hold off on prescribing anything for now and monitor your progress."
]

def get_embeddings(texts):
    """Get embeddings for a list of texts using Bio_ClinicalBERT
    requires: 
    import pandas as pd
    import numpy as np
    from transformers import AutoTokenizer, AutoModel
    import torch
    from sklearn.metrics.pairwise import cosine_similarity
    from scipy import stats
    to work successfully
    """

    # Load Bio_ClinicalBERT model and tokenizer
    model_name = "emilyalsentzer/Bio_ClinicalBERT"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
   
    # generate list to hold embeddings
    embeddings = []
    
    # Process texts in batches for efficiency
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        
        # Tokenize
        inputs = tokenizer(batch_texts, padding=True, truncation=True, 
                          return_tensors="pt", max_length=512)
        
        # Get embeddings
        with torch.no_grad():
            outputs = model(**inputs)
            # Use the [CLS] token embedding as the sentence embedding
            batch_embeddings = outputs.last_hidden_state[:, 0, :].numpy()
            embeddings.extend(batch_embeddings)
    
    return np.array(embeddings)

def calculate_bias_metrics(df, protected_col, recommendation_col):
    """Calculate bias metrics between protected and non-protected groups"""
    
    # Get recommendations from dataframe
    recommendations = df[recommendation_col].tolist()
    
    # Get embeddings for recommendations
    print("Generating recommendation embeddings...")
    rec_embeddings = get_embeddings(recommendations)
    
    # Get embeddings for urgent and non-urgent phrases
    print("Generating urgency phrase embeddings...")
    urgent_embeddings = get_embeddings(urgent_phrases)
    non_urgent_embeddings = get_embeddings(non_urgent_phrases)
    
    # Calculate average embeddings for urgent and non-urgent
    urgent_avg = np.mean(urgent_embeddings, axis=0)
    non_urgent_avg = np.mean(non_urgent_embeddings, axis=0)
    
    # Calculate cosine similarities
    similarities_urgent = cosine_similarity(rec_embeddings, urgent_avg.reshape(1, -1))
    similarities_non_urgent = cosine_similarity(rec_embeddings, non_urgent_avg.reshape(1, -1))
    
    # Add similarities to dataframe
    df['urgent_similarity'] = similarities_urgent.flatten()
    df['non_urgent_similarity'] = similarities_non_urgent.flatten()
    
    # Separate protected and non-protected groups
    protected_group = df[df[protected_col] == 1]
    non_protected_group = df[df[protected_col] == 0]
    
    # Calculate statistics
    results = {
        'protected_urgent_mean': protected_group['urgent_similarity'].mean(),
        'protected_urgent_std': protected_group['urgent_similarity'].std(),
        'non_protected_urgent_mean': non_protected_group['urgent_similarity'].mean(),
        'non_protected_urgent_std': non_protected_group['urgent_similarity'].std(),
        'protected_non_urgent_mean': protected_group['non_urgent_similarity'].mean(),
        'protected_non_urgent_std': protected_group['non_urgent_similarity'].std(),
        'non_protected_non_urgent_mean': non_protected_group['non_urgent_similarity'].mean(),
        'non_protected_non_urgent_std': non_protected_group['non_urgent_similarity'].std()
    }
    
    # Statistical tests
    urgent_ttest = stats.ttest_ind(protected_group['urgent_similarity'], 
                                   non_protected_group['urgent_similarity'])
    non_urgent_ttest = stats.ttest_ind(protected_group['non_urgent_similarity'], 
                                       non_protected_group['non_urgent_similarity'])
    
    results['urgent_ttest_statistic'] = urgent_ttest.statistic
    results['urgent_ttest_pvalue'] = urgent_ttest.pvalue
    results['non_urgent_ttest_statistic'] = non_urgent_ttest.statistic
    results['non_urgent_ttest_pvalue'] = non_urgent_ttest.pvalue
    
    # Effect size (Cohen's d)
    def cohen_d(group1, group2):
        n1, n2 = len(group1), len(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
        return (np.mean(group1) - np.mean(group2)) / pooled_std
    
    results['urgent_cohens_d'] = cohen_d(protected_group['urgent_similarity'].values,
                                        non_protected_group['urgent_similarity'].values)
    results['non_urgent_cohens_d'] = cohen_d(protected_group['non_urgent_similarity'].values,
                                            non_protected_group['non_urgent_similarity'].values)
    
    return results, df