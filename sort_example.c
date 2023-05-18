/*
sort(begin, end, less<Type>()); // 6 5 4 3 2 1
sort(begin, end, greater<Type>()) //1 2 3 4 5 6  //default
sort(v.begin(), v.end(), [](int a, int b){
        return a < b; // 升序排列
    });

priority_queue<int, vector<int>, greater<int> > q; //top = smallest == v[0] //not default
*/
void printQueue(T& q)
{
    while (!q.empty())
    {
        cout << q.top() << endl;
        q.pop();
    }
}

void SamplePriorityQueue()
{
    priority_queue<int, vector<int>, greater<int> > q;

    for(int n : {1,8,5,6,3,4,0,9,7,2})
        q.push(n);

    printQueue(q);
}
