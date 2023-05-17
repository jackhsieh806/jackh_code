/**
 * Definition for singly-linked list.
 * struct ListNode {
 *     int val;
 *     ListNode *next;
 *     ListNode() : val(0), next(nullptr) {}
 *     ListNode(int x) : val(x), next(nullptr) {}
 *     ListNode(int x, ListNode *next) : val(x), next(next) {}
 * };
 */
class Solution {
public:
    ListNode* reverseBetween(ListNode* head, int left, int right) {
        ListNode* th = head;

        while (right > left) {
            th = switchNode(th,left,right);
            left++;
            right--;
        }

        return th;

    }
    ListNode* switchNode(ListNode* head, int left, int right) {
        ListNode* t_head = new ListNode(0,head);
        ListNode* lpre = t_head;
        ListNode* lnode = head;
        ListNode* lnext;
        ListNode* rpre = nullptr;
        ListNode* rnode = head;
        ListNode* rnext;
        
        if (left == right)
            return head;
        if (head == nullptr)
            return head;

        right = right - left;
        while(left > 1){
            lpre = lpre->next;            
            left--;
        }
        lnode = lpre->next;
        lnext = lnode->next;

        if (right == 1) {
            rnode = lnext;
            lpre->next = rnode;
            lnode->next = rnode->next;
            rnode->next = lnode;
            return t_head->next;
        }

        rpre = lpre;
        while(right > 0){
            rpre = rpre->next;            
            right--;
        }

        
        rnode = rpre->next;
        rnext = rnode->next;
        //printf("l val = %d, r val = %d\r\n", lnode->val,rnode->val);
        lpre->next = rnode;
        rnode->next = lnext;
        rpre->next = lnode;
        lnode->next = rnext;

        lpre = t_head->next;
        delete t_head;
        return lpre;

        
    }
};
