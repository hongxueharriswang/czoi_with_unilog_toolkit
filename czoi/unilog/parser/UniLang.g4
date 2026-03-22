grammar UniLang;

@header {
package czoi.unilog.parser;
}

// Lexer rules
ID : [a-zA-Z][a-zA-Z0-9_]* ;
STRING : '"' (~["\\] | '\\' .)* '"' ;
INT : [0-9]+ ;
REAL : [0-9]+ '.' [0-9]+ ;
COMMENT : ('%' | '//') ~[\r\n]* -> skip ;
WS : [ \t\r\n]+ -> skip ;

// Parser rules
start : (signature)? formula* EOF ;

signature : 'signature' '{' declaration* '}' ;
declaration : sortDecl | constDecl | funDecl | predDecl ;
sortDecl : 'sort' ID ('=' '{' ID (',' ID)* '}')? ';' ;
constDecl : 'constant' ID ':' ID ';' ;
funDecl : 'function' ID '(' (ID (',' ID)*)? ')' ':' ID ';' ;
predDecl : 'predicate' ID '(' (ID (',' ID)*)? ')' ';' ;

term : ID ('(' term (',' term)* ')')? ;

formula : atom
        | 'true' | 'false'
        | 'not' formula
        | formula 'and' formula
        | formula 'or' formula
        | formula '->' formula
        | formula '<->' formula
        | 'forall' ID ':' ID '.' formula
        | 'exists' ID ':' ID '.' formula
        // Modal
        | 'box' ('[' ID ']')? formula
        | 'diamond' ('[' ID ']')? formula
        | 'K' '[' ID ']' formula
        | 'B' '[' ID ']' formula
        | 'O' formula
        | 'P' formula
        | 'F' formula   // deontic forbidden (context determines which F)
        // Temporal
        | 'G' ('[' '[' REAL ',' REAL ']' ']')? formula
        | 'F' ('[' '[' REAL ',' REAL ']' ']')? formula
        | 'X' formula
        | formula 'U' ('[' '[' REAL ',' REAL ']' ']')? formula
        | formula 'R' ('[' '[' REAL ',' REAL ']' ']')? formula
        | 'A' formula
        | 'E' formula
        // Dynamic
        | '[' action ']' formula
        | '<' action '>' formula
        // Probabilistic
        | 'P_>=' REAL '(' formula ')'
        | 'P_<=' REAL '(' formula ')'
        | 'P_=' REAL '(' formula ')'
        | 'E' '[' term ']'
        // Fuzzy
        | formula '&G' formula
        | formula '&L' formula
        | formula '&P' formula
        | formula '|G' formula
        | formula '|L' formula
        | formula '|P' formula
        | '~G' formula
        | '~L' formula
        | '~P' formula
        | 'T_>=' REAL '(' formula ')'
        // Non-monotonic
        | formula '=>' formula
        | formula '<' formula
        | 'Opt' '(' formula ')'
        // Description uniLog
        | concept '(' term ')'
        ;

action : ID
       | action ';' action
       | action '|' action
       | action '*'
       | '?' formula
       | '(' action ')'
       ;

concept : ID
        | 'and' '(' concept (',' concept)* ')'
        | 'or' '(' concept (',' concept)* ')'
        | 'not' '(' concept ')'
        | 'some' ID concept
        | 'all' ID concept
        | 'atleast' INT ID concept
        | 'atmost' INT ID concept
        ;

atom : ID '(' term (',' term)* ')' 
     | term '=' term
     | term '!=' term
     ;
