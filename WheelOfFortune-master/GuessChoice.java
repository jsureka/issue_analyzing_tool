import java.util.Scanner;

public class GuessChoice implements Choice {

    @Override
    public boolean selectedChoice(int choice) {
        return choice==2;
    }

    @Override
    public void operation(Player player, GameBoard fortuneBoard, boolean goAgain) {
        System.out.print("Please Enter Your Guess: ");
        Scanner keyboard = new Scanner(System.in);
        String playerGuess = keyboard.next().trim();

        if (!playerGuess.equalsIgnoreCase(fortuneBoard.getPuzzle()))
        {
            System.out.println("\nIncorrect!\n");
            goAgain = false;
        }

        else {
            fortuneBoard.setPendingPuzzle(playerGuess);
        }
    }
}
