import java.util.*;
public class GameBoard {
	
	private StringBuilder availableLetters;
	private final String PUZZLE;
	private StringBuilder pendingPuzzle;
	private String category;
	private char character;

	public GameBoard (String letters, String puzzle, String category)
	{
		
		availableLetters = new StringBuilder(letters.toUpperCase());
		PUZZLE = puzzle;
		this.category = category;
		character = ' ';
		
		pendingPuzzle = new StringBuilder(puzzle);
		
		for (int i=0; i<PUZZLE.length();i++)
		{
			pendingPuzzle.setCharAt(i, character);
					
		}
		
	}
	
	public void setCharacter(char character)
	{
		this.character = character;
	}
	
	public void updateAvailableLetters()
	{
		availableLetters.setCharAt(getIndex(character), ' ');
	}

	private int getIndex(char character) {
		return availableLetters.toString().toLowerCase().indexOf(Character.toLowerCase(character));

	}

	public void displayLetters()
	{
		System.out.println("Available letters - " + availableLetters);
		System.out.println();
	}
	

	public boolean isLetterGuessed(char letterGuess)
	{
		return getIndex(letterGuess) == -1;
	}

	public boolean isLetterInPuzzle(char letterGuess)
	{
		
		boolean status = false;

		for (int index=0; index<PUZZLE.length();index++)
			if (isInPuzzle(letterGuess, index)) {
				status = true;
				break;
			} else
				status = false;
		return status;
	}

	private boolean isInPuzzle(char letterGuess, int index) {
		return Character.toLowerCase(letterGuess) == Character.toLowerCase(PUZZLE.charAt(index));
	}

	public void updatePuzzle()
	{
		for (int i=0; i<PUZZLE.length();i++)
		{
			if (isInPuzzle(character, i))
			pendingPuzzle.setCharAt(i, PUZZLE.charAt(i));
					
		}
	}
	
	public void displayPuzzle()
	{
		System.out.println("Here is the puzzle (" + category + "):");
		
		System.out.print(pendingPuzzle.toString());
		
		System.out.println();
		
		for (int i=0; i<PUZZLE.length();i++)
		{
			
			if (Character.isLetter(PUZZLE.charAt(i))) {
				System.out.print("-");
				
			}
			else
				System.out.print(" ");
					
		}
		
		System.out.println();

	}
	
	public void setPendingPuzzle(String puzzleGuess) 
	{
		pendingPuzzle = new StringBuilder(puzzleGuess.trim());
	}
	
	public String getPendingPuzzle() 
	{
		return this.pendingPuzzle.toString();
	}
	
	public String getPuzzle() 
	{
		return this.PUZZLE;
	}

}
