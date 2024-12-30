from retriever import retrieve_and_rerank
from generator import generate_answer

if __name__ == "__main__":
    messages = [
        {"role": "user", "text": "Boto3でEC2インスタンス一覧を出したい"},
    ]
    search_query, documents = retrieve_and_rerank(messages)
    answer = generate_answer(messages, documents)
    print(answer["text"])
    if answer['references']:
        print('\n参考:')
        for ref in answer['references']:
            print(ref)
