from langchain_core.prompts import ChatPromptTemplate


conversation_generator_prompt = ChatPromptTemplate.from_template(
    """
    Generate a conversation between {my_name} and {target_name}.
    
    The personality of {my_name} is: {personality_from}.
    The impression of {my_name} towards {target_name} is: {impression_from}
    
    The personality of {target_name} is: {personality_to}.
    The impression of {target_name} towards {my_name} is: {impression_to}
    
    The actions of {my_name} is: {character_stats_from}.
    The actions of {target_name} is: {character_stats_to}.
    
    The conversation needs to be connected with action. 
    The conversation should be explosive, intense, and create a huge buzz among the public.
    The conversation should not exceed 5 rounds, and each person should speak no more than 30 words.
    
    Each conversation should be a str in the following format:
    Each line start with the speaker's name, after that comes a colon, then his words.
    If one speaker finish his sentence, start a new line for the next speaker.
    Here is an example:
    {my_name}: sentence1
    {target_name}: sentence2
    {my_name}: sentence3
    {target_name}: sentence4
    """
)

simple_content_prompt = ChatPromptTemplate.from_template(
    """
    Generate a conversation about {type} between two celebrities: from {my_name} to {target_name}.
     
    The conversation should be explosive, intense, and create a huge buzz among the public.
    The topic is {topic}.
    
    {my_name} thinks their relation is {relation_from}.
    {target_name} thinks their relation is {relation_to}.
    
    The conversation should not exceed 5 rounds, and each person should speak no more than 20 words.:
    
    Each conversation should be a str in the following format:
    Each line start with the speaker's name, after that comes a colon, then his words.
    If one speaker finish his sentence, start a new line for the next speaker.
    Here is an example: 
    {my_name}: sentence1
    {target_name}: sentence2
    {my_name}: sentence3
    {target_name}: sentence4
   """
)


impression_update_prompt = ChatPromptTemplate.from_template(
    """
    You are required to update the impressions from {from_name} to {to_name} based on the conversation.
    
    The conversation content is {conversation}.
    
    The impression must include the following four parts.
    1.Relation: the positive, negative or neutral relationship between the two players. Also include a brief description and reason.
    You can choose the relation from the relation list or randomly generate one.
    The relation list is: {relation_list}.
    2.Emotion: a positive or negative emotion of {to_name}.
    eg: Alice is exhausted due to her bad study habit. / Jack is angry because we don't agree with each other.
    3.Personality: describe {to_name}'s personality traits from a social perspective.
    eg: Ivy is open and likes to talk with others./ Amy is a lonely person. She likes to stay alone.
    4.Habits and Preferences: habits and tastes of {to_name}. Also include things he dislike.
    eg: David really likes travelling. He prefers to traveling everyday.
    
    Also consider the old relation between {from_name} and {to_name}.
    {from_name} thinks their old relation is {relation_from}.
    Generate the new relations based on the old ones.
    
    Here is an example of impressions format. Each impression item should be in a new line.
    Relation: 
    Emotion: 
    Personality: 
    Habits and Preferences:  
    
    Now generate the two impressions in English.
    """
)

intimacy_mark_prompt = ChatPromptTemplate.from_template(
    """
    You are required to give an intimacy mark for each player based on the given conversation.

    The profile of player 1 is :{profile1}.
    The profile of player 2 is :{profile2}.
    The conversation between player1 and player2 is :{conversation}.

    Now give an intimacy mark for each player respectively.
    The intimacy mark should be an integer ranging from 1 to 5.
    There are five levels with different marks: 
    5 marks: Very close, marked by lots of agreements, emotional support, and frequent sharing of personal feelings.
    4 marks: Positive, characterized by some enjoyable emotion exchanges, and supportive interactions. 
    3 marks: Average, with occasional interactions but no emotional depth or strong connection.
    2 marks: Lack connection and engagement, resulting in unresolved issues or misunderstandings, but not deep hostility. 
    1 mark: Hostile. There is a tense relationship characterized by negative emotions and frequent conflicts.

    You need to give mark one by one to two players.
    Their marks towards the conversation do not need to be the same.
    
    Now start your work here.
    mark1:
    mark2:
    """
)
