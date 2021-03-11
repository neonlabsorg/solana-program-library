pragma solidity ^0.5.12;

contract helloWorld {
    string constant text = "Hello World!";

    function callHelloWorld() public pure returns (string memory) {
        return text;
    }
}