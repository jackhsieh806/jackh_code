/*
sort(begin, end, less<Type>()); //1 2 3 4 5 6 //default
sort(begin, end, greater<Type>())   // 6 5 4 3 2 1.
sort(v.begin(), v.end(), [](int a, int b){
        return a < b; // 升序排列
    });

priority_queue<int, vector<int>, greater<int> > q; //top = smallest == v[0] //not default
*/

//C++ program to demonstrate the use of priority_queue
#include <iostream>
#include <queue>
using namespace std;
//  
void printQueue(auto& q)
{
    while (!q.empty())
    {
        cout << q.top() << endl;
        q.pop();
    }
}

void SamplePriorityQueue()
{
    //priority_queue<int, vector<int>, greater<int> > q;
    priority_queue<int, vector<int>, less<int> > q;

    for(int n : {1,8,5,6,3,4,0,9,7,2})
        q.push(n);

    printQueue(q);
}

int main() {

	SamplePriorityQueue();	
	return 1;
}
