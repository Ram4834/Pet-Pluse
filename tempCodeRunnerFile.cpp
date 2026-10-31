#include <iostream>
#include <queue>
#include <stack>
#include <string>
using namespace std;
// Abstract base class - generic flight request
class Flight {
protected:
    string id; int requestTime;
public:
    Flight(string i, int t) : id(i), requestTime(t) {}
    virtual ~Flight() {}
    virtual string action() const = 0;   // pure virtual
    virtual string type() const = 0;
    string getId() const { return id; } int getTime() const { return requestTime; }
};
class LandingFlight : public Flight {
public:
    LandingFlight(string i, int t) : Flight(i, t) {}
    string action() const override { return "LANDED"; }
    string type() const override { return "Landing"; }
};
class TakeoffFlight : public Flight {
public:
    TakeoffFlight(string i, int t) : Flight(i, t) {}
    string action() const override { return "TOOK OFF"; }
    string type() const override { return "Take-off"; }
};
class Scheduler {
private:
    queue<Flight*> landQ, takeQ;   // FIFO queues
    stack<string> history;         // LIFO log of completed ops
    int clock = 0, landed = 0, departed = 0;
    void printQueue(queue<Flight*> q, const string& name) {
        cout << name << " queue: ";
        if (q.empty()) cout << "(empty)";
        while (!q.empty()) {
            cout << q.front()->getId() << "(t=" << q.front()->getTime() << ") ";
            q.pop();
        }
        cout << "\n";
    }
public:
    void addFlight(int choice, const string& id) {
        Flight* f;
        if (choice == 1) { f = new LandingFlight(id, clock); landQ.push(f); }
        else             { f = new TakeoffFlight(id, clock); takeQ.push(f); }
        cout << id << " added to " << f->type() << " queue\n";
    }
    void useRunway() {
        clock++;
        Flight* f = nullptr;
        if (!landQ.empty())      { f = landQ.front(); landQ.pop(); landed++; }
        else if (!takeQ.empty()) { f = takeQ.front(); takeQ.pop(); departed++; }
        if (f == nullptr) { cout << "[T=" << clock << "] Runway idle\n"; return; }
        string msg = "[T=" + to_string(clock) + "] " + f->getId() + " " + f->action();
        cout << msg << "\n";
        history.push(msg);
        delete f;
    }
    void showQueues() {
        printQueue(landQ, "Landing");
        printQueue(takeQ, "Take-off");
    }
    void showHistory() {
        stack<string> temp = history;   // copy so original stays intact
        cout << "History (latest first):\n";
        if (temp.empty()) cout << "  (none)\n";
        while (!temp.empty()) { cout << "  " << temp.top() << "\n"; temp.pop(); }
    }
    void showStats() {
        cout << "Landed: " << landed << " | Departed: " << departed
             << " | Waiting: " << landQ.size() + takeQ.size() << "\n";
    }
    ~Scheduler() {
        while (!landQ.empty()) { delete landQ.front(); landQ.pop(); }
        while (!takeQ.empty()) { delete takeQ.front(); takeQ.pop(); }
    }
};
int main() {
    Scheduler s;
    int ch; string id;
    cout << "=== Airport Take-off and Landing Scheduler ===\n";
    do {
        cout << "\n1.Landing Request  2.Take-off Request  3.Use Runway\n"
             << "4.Show Queues  5.Show History  6.Statistics  0.Exit\nChoice: ";
        cin >> ch;
        switch (ch) {
            case 1: case 2: cout << "Flight ID: "; cin >> id; s.addFlight(ch, id); break;
            case 3: s.useRunway(); break;
            case 4: s.showQueues(); break;
            case 5: s.showHistory(); break;
            case 6: s.showStats(); break;
            case 0: cout << "Scheduler closed.\n"; break;
            default: cout << "Invalid choice\n";
        }
    } while (ch != 0);
    return 0;
}