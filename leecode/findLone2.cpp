/******************************************************************************

Welcome to GDB Online.
GDB online is an online compiler and debugger tool for C, C++, Python, Java, PHP, Ruby, Perl,
C#, OCaml, VB, Swift, Pascal, Fortran, Haskell, Objective-C, Assembly, HTML, CSS, JS, SQLite, Prolog.
Code, Compile, Run and Debug online from anywhere in world.

*******************************************************************************/
#include <iostream>
#include <vector>
#include <map>
#include <unordered_map>
using namespace std;

int findLone2(int n, vector<vector<char>> &b);
int main()
{
    vector<int> a;
    vector<vector<char>> test = {{'W', 'B', 'W', 'B', 'B', 'W'},    
                                 {'W', 'B', 'W', 'B', 'B', 'W'},    
                                 {'W', 'B', 'W', 'B', 'B', 'W'},    
                                 {'W', 'W', 'B', 'W', 'B', 'W'}};
    
    int res = 0;
    res = findLone2(3,test);
    
    printf("res = %d\r\n",res);
    return 0;
}

int findLone2(int n, vector<vector<char>> &b) {
    int m = b[0].size();
    int nn = b.size();
    unordered_map<int,int> row;
    unordered_map<int,int> col;
    int res = 0;
    
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < nn ;j++) {
            if (b[j][i] == 'B') {
                row[i]++;
                col[j]++;
            }
        }
    }
    
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < nn ;j++) {    
            if (b[j][i] == 'B') {
                if (row[i] == n && col[j] == n)
                    res++;
            }
        }
    }
    return n;
}
